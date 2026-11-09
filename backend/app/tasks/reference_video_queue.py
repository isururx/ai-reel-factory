"""FIFO worker: download or resume from user-uploaded video, analyze, and persist."""
from __future__ import annotations

import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.page import Page
from app.models.reference_video import ReferenceVideo
from app.models.reference_video_job import ReferenceVideoJob
from app.models.reference_insight import ReferenceCreativeInsight
from app.services.facebook_downloader import FacebookDownloadError, download_public_video
from app.services.reference_video_analysis import analyze_video_file
from app.storage.r2 import download_file, upload_fileobj
from app.worker import celery_app


def _context(job: ReferenceVideoJob) -> dict:
    return {
        "title": job.title,
        "manually_supplied_metrics": {
            "views": job.views_count,
            "reactions": job.reactions_count,
            "shares": job.shares_count,
            "comment_count": job.comments_count,
        },
        "manual_comment_samples": (job.manual_comments or [])[:200],
        "engagement_notes": job.engagement_notes,
        "metrics_provenance": "Manually entered by the user; not independently verified.",
        "comment_sample_limitation": "User-supplied sample; may not represent all comments or viewers.",
    }


@celery_app.task(name="reference_video_queue.drain_next", bind=True)
def drain_next_reference_video_job(self) -> dict:
    """Claim the oldest queued job. Run this worker with concurrency=1 for strict FIFO."""
    db = SessionLocal()
    job_id = None
    try:
        job = db.scalar(
            select(ReferenceVideoJob)
            .where(ReferenceVideoJob.status == "queued")
            .order_by(ReferenceVideoJob.created_at.asc(), ReferenceVideoJob.id.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job is None:
            return {"status": "empty"}
        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        job_id = job.id
        db.commit()

        job = db.get(ReferenceVideoJob, job_id)
        page = db.get(Page, job.page_id)
        if page is None or page.owner_id != job.owner_id:
            raise RuntimeError("The target Page workspace no longer exists.")

        video = db.get(ReferenceVideo, job.reference_video_id) if job.reference_video_id else None
        with TemporaryDirectory(prefix="ai-reel-reference-") as temp_dir:
            if video is not None:
                # The user supplied an MP4 after the public Facebook downloader required login.
                local_path = Path(temp_dir) / video.original_filename
                download_file(video.object_key, str(local_path))
            else:
                try:
                    file_path, detected_title, download_temp_dir = download_public_video(job.source_url)
                except FacebookDownloadError as exc:
                    job.status = "needs_upload"
                    job.error_message = str(exc)[:2000]
                    job.started_at = None
                    db.commit()
                    return {"status": "needs_upload", "job_id": job.id}
                try:
                    path = Path(file_path)
                    size = path.stat().st_size
                    content_type = mimetypes.guess_type(path.name)[0] or "video/mp4"
                    object_key = f"reference-videos/{job.owner_id}/{job.page_id}/{uuid4().hex}{path.suffix.lower() or '.mp4'}"
                    with path.open("rb") as stream:
                        upload_fileobj(stream, object_key, content_type)

                    video = ReferenceVideo(
                        owner_id=job.owner_id,
                        page_id=job.page_id,
                        reference_page_id=None,
                        title=(job.title if job.title != "Reference video" else detected_title)[:200],
                        source_url=job.source_url,
                        object_key=object_key,
                        original_filename=path.name[:255],
                        content_type=content_type,
                        file_size=size,
                        views_count=job.views_count,
                        reactions_count=job.reactions_count,
                        shares_count=job.shares_count,
                        comments_count=job.comments_count,
                        manual_comments=job.manual_comments or [],
                        engagement_notes=job.engagement_notes or "",
                        analysis_status="processing",
                    )
                    db.add(video)
                    db.commit()
                    db.refresh(video)
                    job.reference_video_id = video.id
                    db.commit()
                    local_path = path
                finally:
                    download_temp_dir.cleanup()

            video.analysis_status = "processing"
            db.commit()
            analysis = analyze_video_file(local_path, _context(job))
            video.analysis_status = "completed"
            video.analysis_result = analysis
            video.analyzed_at = datetime.now(timezone.utc)
            db.add(ReferenceCreativeInsight(
                owner_id=job.owner_id,
                page_id=job.page_id,
                reference_video_id=video.id,
                title=f"Creative analysis: {video.title}"[:200],
                content=analysis,
                review_status="pending_review",
            ))
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            job.error_message = None
            db.commit()
            return {"status": "completed", "job_id": job.id, "video_id": video.id}
    except Exception as exc:
        db.rollback()
        if job_id is not None:
            failed = db.get(ReferenceVideoJob, job_id)
            if failed is not None:
                failed.status = "failed"
                failed.completed_at = datetime.now(timezone.utc)
                failed.error_message = str(exc)[:2000]
                if failed.reference_video_id:
                    failed_video = db.get(ReferenceVideo, failed.reference_video_id)
                    if failed_video is not None and failed_video.analysis_status != "completed":
                        failed_video.analysis_status = "failed"
                        failed_video.analysis_result = {"error": str(exc)[:500]}
                db.commit()
        return {"status": "failed", "job_id": job_id, "error": str(exc)[:500]}
    finally:
        db.close()
        if job_id is not None:
            try:
                drain_next_reference_video_job.delay()
            except Exception:
                pass
