from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.database.session import get_db
from app.models.production_pipeline import PagePublishingSettings, ScheduledPublication, ScriptBatch
from app.models.creative_intelligence import CreativePattern
from app.models.page import Page, PageProfile
from app.models.strategy import PageStrategy, StrategyVersion
from app.schemas.scripts import ScriptBatchCreate, ScriptBatchRead
from app.tasks.script_batches import generate_script_batch

router = APIRouter(prefix="/pages/{page_id}/script-batches", tags=["script batches"])


def _owned_page(page_id: int, owner_id: str, db: Session) -> Page:
    page = db.scalar(select(Page).where(Page.id == page_id, Page.owner_id == owner_id))
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found.")
    return page


def _profile_snapshot(profile: PageProfile) -> dict:
    return {
        "niche": profile.niche,
        "target_audience": profile.target_audience,
        "language": profile.language,
        "tone": profile.tone,
        "preferred_formats": profile.preferred_formats,
        "restricted_topics": profile.restricted_topics,
        "fact_check_level": profile.fact_check_level,
    }


def _remaining_daily_slots(page_id: int, owner_id: str, db: Session) -> int:
    settings = db.scalar(select(PagePublishingSettings).where(
        PagePublishingSettings.page_id == page_id,
        PagePublishingSettings.owner_id == owner_id,
    ))
    limit = settings.daily_reel_limit if settings else 2
    timezone_name = settings.timezone if settings else "UTC"
    try:
        local_tz = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=400, detail="The Page publishing timezone is invalid.") from exc

    now_local = datetime.now(timezone.utc).astimezone(local_tz)
    start_local = datetime.combine(now_local.date(), time.min, tzinfo=local_tz)
    end_local = datetime.combine(now_local.date(), time.max, tzinfo=local_tz)
    scheduled_today = db.scalar(select(func.count(ScheduledPublication.id)).where(
        ScheduledPublication.page_id == page_id,
        ScheduledPublication.owner_id == owner_id,
        ScheduledPublication.scheduled_at >= start_local.astimezone(timezone.utc),
        ScheduledPublication.scheduled_at <= end_local.astimezone(timezone.utc),
        ScheduledPublication.status.in_(["scheduled", "publishing", "published"]),
    )) or 0
    return max(0, limit - int(scheduled_today))


@router.post("", response_model=ScriptBatchRead, status_code=status.HTTP_202_ACCEPTED)
def create_script_batch(
    page_id: int,
    payload: ScriptBatchCreate,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    _owned_page(page_id, user.id, db)
    profile = db.scalar(select(PageProfile).where(PageProfile.page_id == page_id))
    if profile is None:
        raise HTTPException(status_code=400, detail="Configure this Page profile before generating scripts.")

    strategy = db.scalar(select(PageStrategy).where(
        PageStrategy.id == payload.strategy_id,
        PageStrategy.page_id == page_id,
    ))
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found for this Page.")
    strategy_version = db.scalar(select(StrategyVersion).where(
        StrategyVersion.id == payload.strategy_version_id,
        StrategyVersion.strategy_id == strategy.id,
    ))
    if strategy_version is None:
        raise HTTPException(status_code=404, detail="Strategy version does not belong to the selected strategy.")

    if payload.fill_remaining_daily_slots:
        count = _remaining_daily_slots(page_id, user.id, db)
        if count < 1:
            raise HTTPException(status_code=409, detail="This Page has no remaining publishing slots today.")
    else:
        if payload.script_count is None:
            raise HTTPException(status_code=422, detail="script_count is required unless filling remaining daily slots.")
        count = payload.script_count

    if payload.pattern_selection == "manual" and not payload.pattern_ids:
        raise HTTPException(status_code=422, detail="Select at least one creative pattern for manual selection.")

    selected_patterns: list[CreativePattern] = []
    if payload.pattern_selection in ("manual", "hybrid"):
        selected_patterns = list(db.scalars(select(CreativePattern).where(
            CreativePattern.owner_id == user.id,
            CreativePattern.page_id == page_id,
            CreativePattern.id.in_(payload.pattern_ids),
        )).all())
        if len(selected_patterns) != len(set(payload.pattern_ids)):
            raise HTTPException(status_code=422, detail="One or more selected patterns do not belong to this Page.")

    if payload.pattern_selection in ("automatic", "hybrid"):
        auto_patterns = list(db.scalars(
            select(CreativePattern).where(
                CreativePattern.owner_id == user.id,
                CreativePattern.page_id == page_id,
                CreativePattern.status.in_(["active", "emerging"]),
            ).order_by(
                CreativePattern.status.asc(),
                CreativePattern.supporting_video_count.desc(),
                CreativePattern.occurrence_count.desc(),
            ).limit(5)
        ).all())
        known_ids = {pattern.id for pattern in selected_patterns}
        selected_patterns.extend(pattern for pattern in auto_patterns if pattern.id not in known_ids)

    pattern_snapshot = [{
        "id": pattern.id,
        "category": pattern.category,
        "name": pattern.name,
        "description": pattern.description,
        "reusable_construction": pattern.reusable_construction,
        "confidence_score": pattern.confidence_score,
    } for pattern in selected_patterns]

    snapshot = {
        "brief": payload.brief,
        "source_url": str(payload.source_url) if payload.source_url else None,
        "profile": _profile_snapshot(profile),
        "strategy": strategy_version.configuration,
        "creative_patterns": pattern_snapshot,
        "creative_pattern_ids": [pattern.id for pattern in selected_patterns],
        "pattern_selection": payload.pattern_selection,
    }
    batch = ScriptBatch(
        owner_id=user.id,
        page_id=page_id,
        strategy_id=strategy.id,
        strategy_version_id=strategy_version.id,
        mode=payload.mode,
        status="queued",
        requested_count=count,
        completed_count=0,
        input_snapshot=snapshot,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    try:
        generate_script_batch.delay(batch.id)
    except Exception as exc:
        # Keep the durable queued record so it can be safely re-enqueued later.
        raise HTTPException(
            status_code=503,
            detail="Batch saved, but Redis could not notify the Celery worker. Start Redis and the worker, then retry the queued batch.",
        ) from exc
    return batch


@router.get("", response_model=list[ScriptBatchRead])
def list_script_batches(
    page_id: int,
    user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    _owned_page(page_id, user.id, db)
    return list(db.scalars(
        select(ScriptBatch).where(
            ScriptBatch.page_id == page_id,
            ScriptBatch.owner_id == user.id,
        ).order_by(ScriptBatch.created_at.desc()).limit(limit)
    ).all())


@router.get("/{batch_id}", response_model=ScriptBatchRead)
def get_script_batch(
    page_id: int,
    batch_id: int,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    _owned_page(page_id, user.id, db)
    batch = db.scalar(select(ScriptBatch).where(
        ScriptBatch.id == batch_id,
        ScriptBatch.page_id == page_id,
        ScriptBatch.owner_id == user.id,
    ))
    if batch is None:
        raise HTTPException(status_code=404, detail="Script batch not found.")
    return batch
