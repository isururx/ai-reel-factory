from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.database.session import get_db
from app.models.creative_intelligence import CreativeElement, CreativePattern, PatternEvidence
from app.models.page import Page
from app.schemas.creative_intelligence import CreativeElementRead, CreativePatternRead, PatternEvidenceRead

router = APIRouter(prefix="/pages/{page_id}/creative-intelligence", tags=["creative intelligence"])


def _owned_page(page_id: int, user: CurrentUser, db: Session) -> None:
    page = db.scalar(select(Page.id).where(Page.id == page_id, Page.owner_id == user.id))
    if page is None:
        raise HTTPException(status_code=404, detail="Page workspace not found.")


@router.get("/patterns", response_model=list[CreativePatternRead])
def list_patterns(
    page_id: int,
    user: CurrentUser,
    category: str | None = Query(default=None, max_length=40),
    status: str | None = Query(default=None, pattern="^(emerging|active|archived)$"),
    db: Session = Depends(get_db),
):
    _owned_page(page_id, user, db)
    query = select(CreativePattern).where(
        CreativePattern.owner_id == user.id,
        CreativePattern.page_id == page_id,
    )
    if category:
        query = query.where(CreativePattern.category == category)
    if status:
        query = query.where(CreativePattern.status == status)
    return list(db.scalars(query.order_by(
        CreativePattern.supporting_video_count.desc(),
        CreativePattern.occurrence_count.desc(),
        CreativePattern.updated_at.desc(),
    )).all())


@router.get("/elements", response_model=list[CreativeElementRead])
def list_elements(
    page_id: int,
    user: CurrentUser,
    video_id: int | None = None,
    element_type: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    _owned_page(page_id, user, db)
    query = select(CreativeElement).where(
        CreativeElement.owner_id == user.id,
        CreativeElement.page_id == page_id,
    )
    if video_id is not None:
        query = query.where(CreativeElement.reference_video_id == video_id)
    if element_type:
        query = query.where(CreativeElement.element_type == element_type)
    return list(db.scalars(query.order_by(CreativeElement.created_at.desc()).limit(limit)).all())


@router.get("/patterns/{pattern_id}/evidence", response_model=list[PatternEvidenceRead])
def list_pattern_evidence(page_id: int, pattern_id: int, user: CurrentUser, db: Session = Depends(get_db)):
    _owned_page(page_id, user, db)
    pattern = db.scalar(select(CreativePattern.id).where(
        CreativePattern.id == pattern_id,
        CreativePattern.owner_id == user.id,
        CreativePattern.page_id == page_id,
    ))
    if pattern is None:
        raise HTTPException(status_code=404, detail="Creative pattern not found.")
    return list(db.scalars(select(PatternEvidence).where(
        PatternEvidence.pattern_id == pattern_id
    ).order_by(PatternEvidence.created_at.desc())).all())


@router.get("/summary")
def creative_intelligence_summary(page_id: int, user: CurrentUser, db: Session = Depends(get_db)):
    _owned_page(page_id, user, db)
    patterns = db.scalar(select(func.count(CreativePattern.id)).where(
        CreativePattern.owner_id == user.id, CreativePattern.page_id == page_id
    )) or 0
    elements = db.scalar(select(func.count(CreativeElement.id)).where(
        CreativeElement.owner_id == user.id, CreativeElement.page_id == page_id
    )) or 0
    active = db.scalar(select(func.count(CreativePattern.id)).where(
        CreativePattern.owner_id == user.id, CreativePattern.page_id == page_id,
        CreativePattern.status == "active",
    )) or 0
    return {"patterns_count": int(patterns), "elements_count": int(elements), "active_patterns_count": int(active)}
