from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.database.session import get_db
from app.models.reference_insight import ReferenceCreativeInsight
from app.models.page import Page
from app.schemas.reference_videos import ReferenceInsightRead, ReferenceInsightReview

router = APIRouter(prefix="/pages/{page_id}/reference-insights", tags=["reference insights"])


def _owned_page(page_id: int, user: CurrentUser, db: Session) -> Page:
    page = db.scalar(select(Page).where(Page.id == page_id, Page.owner_id == user.id))
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found.")
    return page


@router.get("", response_model=list[ReferenceInsightRead])
def list_reference_insights(page_id: int, user: CurrentUser, db: Session = Depends(get_db)):
    _owned_page(page_id, user, db)
    return list(db.scalars(select(ReferenceCreativeInsight).where(
        ReferenceCreativeInsight.page_id == page_id,
        ReferenceCreativeInsight.owner_id == user.id,
    ).order_by(ReferenceCreativeInsight.created_at.desc())).all())


@router.patch("/{insight_id}/review", response_model=ReferenceInsightRead)
def review_reference_insight(page_id: int, insight_id: int, payload: ReferenceInsightReview,
                             user: CurrentUser, db: Session = Depends(get_db)):
    _owned_page(page_id, user, db)
    insight = db.scalar(select(ReferenceCreativeInsight).where(
        ReferenceCreativeInsight.id == insight_id,
        ReferenceCreativeInsight.page_id == page_id,
        ReferenceCreativeInsight.owner_id == user.id,
    ))
    if insight is None:
        raise HTTPException(status_code=404, detail="Reference insight not found.")
    insight.review_status = payload.review_status
    insight.reviewer_notes = payload.reviewer_notes
    db.commit()
    db.refresh(insight)
    return insight
