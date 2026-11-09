"""FIFO worker: download or resume from user-uploaded video, analyze, and persist."""
from __future__ import annotations

import mimetypes
import shutil
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from sqlalchemy import func, select

from app.database.session import SessionLocal
from app.models.page import Page
from app.models.reference_video import ReferenceVideo
from app.models.reference_video_job import ReferenceVideoJob
from app.models.reference_video_analysis_attempt import ReferenceVideoAnalysisAttempt
from app.models.reference_insight import ReferenceCreativeInsight
from app.services.creative_intelligence import persist_creative_intelligence
from app.services.facebook_downloader import FacebookDownloadError, download_public_video
from app.services.reference_video_analysis import analyze_video_with_fallback
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
                local_path = Path(temp_dir) / video.original_filename
                download_file(video.object_key, str(local_path))
            else:
                download_temp_dir = None
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
                    local_path = Path(temp_dir) / path.name
                    shutil.copy2(path, local_path)
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
                    local_path = Path(temp_dir) / path.name
                    shutil.copy2(path, local_path)
                finally:
                    if download_temp_dir is not None:
                        download_temp_dir.cleanup()

            video.analysis_status = "processing"
            db.commit()
            prior_attempt_count = db.scalar(select(func.count(ReferenceVideoAnalysisAttempt.id)).where(
                ReferenceVideoAnalysisAttempt.reference_video_id == video.id,
                ReferenceVideoAnalysisAttempt.owner_id == job.owner_id,
            )) or 0
            prior_duration_ms = db.scalar(select(func.sum(ReferenceVideoAnalysisAttempt.duration_ms)).where(
                ReferenceVideoAnalysisAttempt.reference_video_id == video.id,
                ReferenceVideoAnalysisAttempt.owner_id == job.owner_id,
            )) or 0
            try:
                execution = analyze_video_with_fallback(
                    local_path, _context(job), object_key=video.object_key,
                    primary_provider=job.analysis_primary_provider, primary_model=job.analysis_primary_model,
                )
            except Exception as analysis_exc:
                for index, attempt in enumerate(getattr(analysis_exc, "attempts", []), start=1):
                    db.add(ReferenceVideoAnalysisAttempt(
                        owner_id=job.owner_id, page_id=job.page_id, reference_video_id=video.id,
                        job_id=job.id, attempt_number=prior_attempt_count + index, provider=attempt.provider,
                        model_id=attempt.model_id, status=attempt.status, error_code=attempt.error_code,
                        error_message=attempt.error_message, duration_ms=attempt.duration_ms,
                        input_tokens=attempt.input_tokens, output_tokens=attempt.output_tokens,
                        started_at=attempt.started_at, completed_at=attempt.completed_at,
                    ))
                db.commit()
                raise

            analysis = execution.result
            video.analysis_status = "completed"
            video.analysis_result = analysis
            video.analysis_provider = execution.provider
            video.analysis_model = execution.model_id
            video.analysis_attempt_count = prior_attempt_count + len(execution.attempts)
            video.analysis_total_duration_ms = prior_duration_ms + execution.total_duration_ms
            video.analyzed_at = datetime.now(timezone.utc)
            for index, attempt in enumerate(execution.attempts, start=1):
                db.add(ReferenceVideoAnalysisAttempt(
                    owner_id=job.owner_id, page_id=job.page_id, reference_video_id=video.id,
                    job_id=job.id, attempt_number=prior_attempt_count + index, provider=attempt.provider,
                    model_id=attempt.model_id, status=attempt.status, error_code=attempt.error_code,
                    error_message=attempt.error_message, duration_ms=attempt.duration_ms,
                    input_tokens=attempt.input_tokens, output_tokens=attempt.output_tokens,
                    started_at=attempt.started_at, completed_at=attempt.completed_at,
                ))
            intelligence_result = persist_creative_intelligence(
                db, owner_id=job.owner_id, page_id=page.id, video=video, analysis=analysis
            )
            db.add(ReferenceCreativeInsight(
                owner_id=job.owner_id,
                page_id=job.page_id,
                reference_video_id=video.id,
                title=f"Creative analysis: {video.title}"[:200],
                content={**analysis, "creative_intelligence_persistence": intelligence_result},
                review_status="pending_review",
            ))
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            job.error_message = None
            db.commit()
            return {
                "status": "completed",
                "job_id": job.id,
                "video_id": video.id,
                "creative_intelligence": intelligence_result,
            }
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
                        failed_video.analysis_attempt_count = db.scalar(select(func.count(
                            ReferenceVideoAnalysisAttempt.id
                        )).where(
                            ReferenceVideoAnalysisAttempt.reference_video_id == failed_video.id,
                            ReferenceVideoAnalysisAttempt.owner_id == job.owner_id,
                        )) or 0
                        failed_video.analysis_total_duration_ms = db.scalar(select(func.sum(
                            ReferenceVideoAnalysisAttempt.duration_ms
                        )).where(
                            ReferenceVideoAnalysisAttempt.reference_video_id == failed_video.id,
                            ReferenceVideoAnalysisAttempt.owner_id == job.owner_id,
                        ))
                db.commit()
        return {"status": "failed", "job_id": job_id, "error": str(exc)[:500]}
    finally:
        db.close()
        if job_id is not None:
            try:
                drain_next_reference_video_job.delay()
            except Exception:
                pass
