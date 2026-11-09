import json
import mimetypes
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.database.session import get_db
from app.models.reference import ReferencePage
from app.models.reference_video import ReferenceVideo
from app.models.reference_insight import ReferenceCreativeInsight
from app.schemas.reference_videos import ReferenceVideoManualUpdate, ReferenceVideoRead
from app.services.facebook_downloader import FacebookDownloadError, download_public_video
from app.storage.r2 import create_download_url, download_file, upload_fileobj
from app.services.reference_video_analysis import analyze_video_file

router = APIRouter(prefix="/pages/{page_id}/references/{reference_id}/videos", tags=["reference videos"])
MAX_VIDEO_BYTES = 300 * 1024 * 1024
ALLOWED_TYPES = {"video/mp4", "video/webm", "video/quicktime", "video/x-matroska"}


def _reference(page_id: int, reference_id: int, owner_id: str, db: Session) -> ReferencePage:
    reference = db.scalar(select(ReferencePage).where(
        ReferencePage.id == reference_id,
        ReferencePage.page_id == page_id,
        ReferencePage.owner_id == owner_id,
    ))
    if reference is None:
        raise HTTPException(status_code=404, detail="Reference Page not found.")
    return reference


def _store_video(db: Session, user: CurrentUser, reference_id: int, fileobj, filename: str,
                 content_type: str, size: int, title: str, source_url: str | None,
                 manual_comments: list[str], views_count: int | None, reactions_count: int | None,
                 shares_count: int | None, comments_count: int | None, engagement_notes: str) -> ReferenceVideo:
    suffix = Path(filename).suffix.lower()[:12] or mimetypes.guess_extension(content_type) or ".mp4"
    object_key = f"reference-videos/{user.id}/{reference_id}/{uuid4().hex}{suffix}"
    try:
        upload_fileobj(fileobj, object_key, content_type)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not store the video in Cloudflare R2. Check backend R2 configuration.") from exc
    video = ReferenceVideo(
        owner_id=user.id, reference_page_id=reference_id, title=title[:200] or "Reference video",
        source_url=source_url, object_key=object_key, original_filename=Path(filename).name[:255],
        content_type=content_type, file_size=size, manual_comments=manual_comments,
        views_count=views_count, reactions_count=reactions_count, shares_count=shares_count,
        comments_count=comments_count, engagement_notes=engagement_notes,
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


@router.get("", response_model=list[ReferenceVideoRead])
def list_reference_videos(page_id: int, reference_id: int, user: CurrentUser,
                          db: Session = Depends(get_db)):
    reference = _reference(page_id, reference_id, user.id, db)
    return list(db.scalars(select(ReferenceVideo).where(
        ReferenceVideo.reference_page_id == reference.id,
        ReferenceVideo.owner_id == user.id,
    ).order_by(ReferenceVideo.created_at.desc())).all())


@router.post("", response_model=ReferenceVideoRead, status_code=201)
async def upload_reference_video(
    page_id: int, reference_id: int, user: CurrentUser,
    file: UploadFile = File(...),
    title: str = Form("Reference video"),
    source_url: str | None = Form(None),
    views_count: int | None = Form(None),
    reactions_count: int | None = Form(None),
    shares_count: int | None = Form(None),
    comments_count: int | None = Form(None),
    manual_comments_json: str = Form("[]"),
    engagement_notes: str = Form(""),
    db: Session = Depends(get_db),
):
    reference = _reference(page_id, reference_id, user.id, db)
    validated_reference_id = reference.id
    # Do not hold a Supabase connection while a potentially large file is uploaded to R2.
    db.close()
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Upload an MP4, WebM, MOV or MKV video.")
    try:
        manual_comments = json.loads(manual_comments_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="Manual comments must be valid JSON.") from exc
    if not isinstance(manual_comments, list) or not all(isinstance(item, str) for item in manual_comments):
        raise HTTPException(status_code=422, detail="Manual comments must be a JSON array of text strings.")
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size <= 0 or size > MAX_VIDEO_BYTES:
        raise HTTPException(status_code=413, detail="Video must be between 1 byte and 300 MB.")
    return _store_video(db, user, validated_reference_id, file.file, file.filename or "reference-video.mp4",
                        content_type, size, title, source_url, manual_comments[:200],
                        views_count, reactions_count, shares_count, comments_count, engagement_notes)


@router.post("/import-facebook", response_model=ReferenceVideoRead, status_code=201)
def import_public_facebook_video(
    page_id: int, reference_id: int, user: CurrentUser,
    url: str = Form(...), title: str = Form("Reference video"),
    views_count: int | None = Form(None), reactions_count: int | None = Form(None),
    shares_count: int | None = Form(None), comments_count: int | None = Form(None),
    manual_comments_json: str = Form("[]"), engagement_notes: str = Form(""),
    db: Session = Depends(get_db),
):
    reference = _reference(page_id, reference_id, user.id, db)
    validated_reference_id = reference.id
    # Release the DB connection before yt-dlp and the subsequent R2 upload.
    db.close()
    try:
        comments = json.loads(manual_comments_json)
        if not isinstance(comments, list) or not all(isinstance(item, str) for item in comments):
            raise ValueError("Manual comments must be a JSON array of strings.")
        file_path, detected_title, temp_dir = download_public_video(url)
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FacebookDownloadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        path = Path(file_path)
        size = path.stat().st_size
        if size > MAX_VIDEO_BYTES:
            raise HTTPException(status_code=413, detail="Video exceeds the 300 MB ingestion limit.")
        content_type = mimetypes.guess_type(path.name)[0] or "video/mp4"
        if content_type not in ALLOWED_TYPES:
            content_type = "video/mp4"
        with path.open("rb") as stream:
            return _store_video(db, user, validated_reference_id, stream, path.name, content_type, size,
                                title if title != "Reference video" else detected_title, url,
                                comments[:200], views_count, reactions_count, shares_count,
                                comments_count, engagement_notes)
    finally:
        temp_dir.cleanup()


@router.patch("/{video_id}", response_model=ReferenceVideoRead)
def update_manual_video_context(page_id: int, reference_id: int, video_id: int,
                                payload: ReferenceVideoManualUpdate, user: CurrentUser,
                                db: Session = Depends(get_db)):
    reference = _reference(page_id, reference_id, user.id, db)
    video = db.scalar(select(ReferenceVideo).where(
        ReferenceVideo.id == video_id, ReferenceVideo.reference_page_id == reference.id,
        ReferenceVideo.owner_id == user.id,
    ))
    if video is None:
        raise HTTPException(status_code=404, detail="Reference video not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(video, key, value)
    db.commit()
    db.refresh(video)
    return video


@router.get("/{video_id}/file")
def get_reference_video_file(page_id: int, reference_id: int, video_id: int,
                             user: CurrentUser, db: Session = Depends(get_db)):
    reference = _reference(page_id, reference_id, user.id, db)
    video = db.scalar(select(ReferenceVideo).where(
        ReferenceVideo.id == video_id, ReferenceVideo.reference_page_id == reference.id,
        ReferenceVideo.owner_id == user.id,
    ))
    if video is None:
        raise HTTPException(status_code=404, detail="Reference video not found.")
    try:
        return {"url": create_download_url(video.object_key), "expires_in": 900}
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not create a temporary video URL.") from exc



@router.post("/{video_id}/analyze", response_model=ReferenceVideoRead)
def analyze_reference_video(page_id: int, reference_id: int, video_id: int,
                            user: CurrentUser, db: Session = Depends(get_db)):
    """Run Gemini multimodal analysis and save Page-scoped insights for human review."""
    reference = _reference(page_id, reference_id, user.id, db)
    video = db.scalar(select(ReferenceVideo).where(
        ReferenceVideo.id == video_id,
        ReferenceVideo.reference_page_id == reference.id,
        ReferenceVideo.owner_id == user.id,
    ))
    if video is None:
        raise HTTPException(status_code=404, detail="Reference video not found.")
    if video.analysis_status == "processing":
        raise HTTPException(status_code=409, detail="This video is already being analyzed.")

    video.analysis_status = "processing"
    video.analysis_result = {}
    db.commit()
    object_key = video.object_key
    filename = video.original_filename
    context = {
        "title": video.title,
        "manually_supplied_metrics": {
            "views": video.views_count,
            "reactions": video.reactions_count,
            "shares": video.shares_count,
            "comment_count": video.comments_count,
        },
        "manual_comment_samples": (video.manual_comments or [])[:200],
        "engagement_notes": video.engagement_notes,
        "metrics_provenance": "Manually entered by the user; not independently verified.",
        "comment_sample_limitation": "User-supplied sample; may not represent all comments or viewers.",
    }
    db.close()

    try:
        suffix = Path(filename).suffix.lower() or ".mp4"
        with tempfile.TemporaryDirectory(prefix="ai-reel-analysis-") as temp_dir:
            local_path = Path(temp_dir) / f"reference{suffix}"
            download_file(object_key, str(local_path))
            analysis = analyze_video_file(local_path, context)

        # Reuse the request session only after the long R2/Gemini work has finished.
        video = db.scalar(select(ReferenceVideo).where(
            ReferenceVideo.id == video_id,
            ReferenceVideo.reference_page_id == reference_id,
            ReferenceVideo.owner_id == user.id,
        ))
        if video is None:
            raise HTTPException(status_code=404, detail="Reference video was removed during analysis.")
        video.analysis_status = "completed"
        video.analysis_result = analysis
        video.analyzed_at = datetime.now(timezone.utc)
        insight = ReferenceCreativeInsight(
            owner_id=user.id,
            page_id=page_id,
            reference_video_id=video.id,
            title=f"Creative analysis: {video.title}"[:200],
            content=analysis,
            review_status="pending_review",
        )
        db.add(insight)
        db.commit()
        db.refresh(video)
        return video
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        failed_video = db.scalar(select(ReferenceVideo).where(
            ReferenceVideo.id == video_id,
            ReferenceVideo.reference_page_id == reference_id,
            ReferenceVideo.owner_id == user.id,
        ))
        if failed_video is not None:
            failed_video.analysis_status = "failed"
            failed_video.analysis_result = {"error": str(exc)[:500]}
            db.commit()
        raise HTTPException(status_code=502, detail=f"Video analysis failed: {str(exc)[:300]}") from exc
