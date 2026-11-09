from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
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
from app.storage.r2 import create_download_url

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
