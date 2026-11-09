from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.database.session import get_db
from app.models.page import Page
from app.models.reference_video import ReferenceVideo
from app.models.reference_video_job import ReferenceVideoJob
from app.schemas.reference_video_queue import (
    ReferenceVideoQueueCreate, ReferenceVideoQueueJobList,
    ReferenceVideoQueueJobRead, ReferenceVideoRead,
)
from app.services.facebook_downloader import FacebookDownloadError, validate_facebook_url
from app.tasks.reference_video_queue import drain_next_reference_video_job
from app.storage.r2 import create_download_url, upload_fileobj

router = APIRouter(prefix="/pages/{page_id}/reference-videos", tags=["reference video queue"])


def _owned_page(page_id: int, user: CurrentUser, db: Session) -> Page:
    page = db.scalar(select(Page).where(Page.id == page_id, Page.owner_id == user.id))
    if page is None:
        raise HTTPException(status_code=404, detail="Page workspace not found.")
    return page


@router.post("/queue", response_model=ReferenceVideoQueueJobRead, status_code=202)
def enqueue_reference_video(page_id: int, payload: ReferenceVideoQueueCreate,
                            user: CurrentUser, db: Session = Depends(get_db)):
    _owned_page(page_id, user, db)
    source_url = str(payload.source_url)
    try:
        validate_facebook_url(source_url)
    except FacebookDownloadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    job = ReferenceVideoJob(
        owner_id=user.id,
        page_id=page_id,
        source_url=source_url,
        title=payload.title.strip() or "Reference video",
        views_count=payload.views_count,
        reactions_count=payload.reactions_count,
        shares_count=payload.shares_count,
        comments_count=payload.comments_count,
        manual_comments=payload.manual_comments,
        engagement_notes=payload.engagement_notes,
        analysis_primary_provider=payload.analysis_primary_provider,
        analysis_primary_model=payload.analysis_primary_model,
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    position = db.scalar(select(func.count(ReferenceVideoJob.id)).where(
        ReferenceVideoJob.status == "queued",
        (ReferenceVideoJob.created_at < job.created_at) |
        ((ReferenceVideoJob.created_at == job.created_at) & (ReferenceVideoJob.id <= job.id)),
    )) or 1
    job.queue_position = int(position)
    db.commit()
    db.refresh(job)

    try:
        # A drain task always claims the oldest queued DB record, not necessarily this job.
        drain_next_reference_video_job.delay()
    except Exception as exc:
        job.error_message = "Saved in the database, but the worker could not be notified. Check Redis and start the worker."
        db.commit()
        raise HTTPException(status_code=503, detail=job.error_message) from exc
    return job


@router.post("/queue/{job_id}/retry", response_model=ReferenceVideoQueueJobRead, status_code=202)
def retry_failed_reference_video_job(
    page_id: int,
    job_id: int,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Requeue a failed analysis while preserving its URL and manually entered context."""
    _owned_page(page_id, user, db)
    job = db.scalar(select(ReferenceVideoJob).where(
        ReferenceVideoJob.id == job_id,
        ReferenceVideoJob.page_id == page_id,
        ReferenceVideoJob.owner_id == user.id,
    ))
    if job is None:
        raise HTTPException(status_code=404, detail="Queue job not found.")
    if job.status != "failed":
        raise HTTPException(status_code=409, detail="Only failed jobs can be retried.")

    # A retry joins the back of the FIFO queue rather than jumping ahead of
    # jobs submitted while the original attempt was running.
    job.status = "queued"
    job.created_at = datetime.now(timezone.utc)
    job.queue_position = None
    job.started_at = None
    job.completed_at = None
    job.error_message = None
    if job.reference_video_id is not None:
        video = db.get(ReferenceVideo, job.reference_video_id)
        if video is not None:
            video.analysis_status = "pending"
            video.analysis_result = {}
            video.analyzed_at = None
    db.commit()
    db.refresh(job)

    position = db.scalar(select(func.count(ReferenceVideoJob.id)).where(
        ReferenceVideoJob.status == "queued",
        (ReferenceVideoJob.created_at < job.created_at) |
        ((ReferenceVideoJob.created_at == job.created_at) & (ReferenceVideoJob.id <= job.id)),
    )) or 1
    job.queue_position = int(position)
    db.commit()
    db.refresh(job)

    try:
        drain_next_reference_video_job.delay()
    except Exception as exc:
        job.error_message = "Retry saved in the queue, but the worker could not be notified. Check Redis and start the worker."
        db.commit()
        raise HTTPException(status_code=503, detail=job.error_message) from exc
    return job


@router.get("/queue", response_model=ReferenceVideoQueueJobList)
def list_reference_video_jobs(page_id: int, user: CurrentUser, db: Session = Depends(get_db)):
    _owned_page(page_id, user, db)
    jobs = list(db.scalars(select(ReferenceVideoJob).where(
        ReferenceVideoJob.page_id == page_id,
        ReferenceVideoJob.owner_id == user.id,
    ).order_by(ReferenceVideoJob.created_at.desc(), ReferenceVideoJob.id.desc()).limit(100)).all())

    queued = list(db.scalars(select(ReferenceVideoJob).where(
        ReferenceVideoJob.status == "queued"
    ).order_by(ReferenceVideoJob.created_at.asc(), ReferenceVideoJob.id.asc())).all())
    positions = {item.id: index + 1 for index, item in enumerate(queued)}
    for item in jobs:
        item.queue_position = positions.get(item.id)

    return ReferenceVideoQueueJobList(
        jobs=jobs,
        queued_count=len(queued),
        processing_count=sum(1 for item in jobs if item.status == "processing"),
    )


@router.get("", response_model=list[ReferenceVideoRead])
def list_page_reference_videos(page_id: int, user: CurrentUser, db: Session = Depends(get_db)):
    _owned_page(page_id, user, db)
    return list(db.scalars(select(ReferenceVideo).where(
        ReferenceVideo.page_id == page_id,
        ReferenceVideo.owner_id == user.id,
        ReferenceVideo.analysis_status == "completed",
    ).order_by(ReferenceVideo.analyzed_at.desc(), ReferenceVideo.id.desc())).all())


@router.get("/{video_id}/file")
def get_page_reference_video_file(page_id: int, video_id: int,
                                  user: CurrentUser, db: Session = Depends(get_db)):
    _owned_page(page_id, user, db)
    video = db.scalar(select(ReferenceVideo).where(
        ReferenceVideo.id == video_id,
        ReferenceVideo.page_id == page_id,
        ReferenceVideo.owner_id == user.id,
    ))
    if video is None:
        raise HTTPException(status_code=404, detail="Analyzed video not found.")
    return {"url": create_download_url(video.object_key), "expires_in": 900}



@router.post("/queue/{job_id}/upload", response_model=ReferenceVideoQueueJobRead, status_code=202)
async def upload_video_for_queued_job(
    page_id: int,
    job_id: int,
    user: CurrentUser,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Attach a user-provided video to a job whose public URL required authentication."""
    from pathlib import Path
    from uuid import uuid4
    from app.storage.r2 import upload_fileobj

    _owned_page(page_id, user, db)
    job = db.scalar(select(ReferenceVideoJob).where(
        ReferenceVideoJob.id == job_id,
        ReferenceVideoJob.page_id == page_id,
        ReferenceVideoJob.owner_id == user.id,
    ))
    if job is None:
        raise HTTPException(status_code=404, detail="Queue job not found.")
    if job.status != "needs_upload":
        raise HTTPException(status_code=409, detail="This job is not waiting for a manual video upload.")

    allowed_types = {"video/mp4", "video/webm", "video/quicktime", "video/x-matroska"}
    content_type = (file.content_type or "").lower()
    if content_type not in allowed_types:
        raise HTTPException(status_code=415, detail="Upload an MP4, WebM, MOV or MKV video.")
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size <= 0 or size > 300 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Video must be between 1 byte and 300 MB.")

    suffix = Path(file.filename or "reference-video.mp4").suffix.lower()[:12] or ".mp4"
    object_key = f"reference-videos/{user.id}/{page_id}/{uuid4().hex}{suffix}"
    try:
        upload_fileobj(file.file, object_key, content_type)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not store the uploaded video in Cloudflare R2.") from exc

    video = ReferenceVideo(
        owner_id=user.id,
        page_id=page_id,
        reference_page_id=None,
        title=job.title,
        source_url=job.source_url,
        object_key=object_key,
        original_filename=Path(file.filename or "reference-video.mp4").name[:255],
        content_type=content_type,
        file_size=size,
        views_count=job.views_count,
        reactions_count=job.reactions_count,
        shares_count=job.shares_count,
        comments_count=job.comments_count,
        manual_comments=job.manual_comments or [],
        engagement_notes=job.engagement_notes or "",
        analysis_status="pending",
    )
    db.add(video)
    db.flush()
    job.reference_video_id = video.id
    job.status = "queued"
    job.error_message = None
    job.started_at = None
    job.completed_at = None
    db.commit()
    db.refresh(job)
    try:
        drain_next_reference_video_job.delay()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Video uploaded and queued in the database, but Redis could not notify the worker. Start Redis and the Celery worker.") from exc
    return job
