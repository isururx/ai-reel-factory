from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.database.session import get_db
from app.models.page import Page
from app.models.trend import PageTrendRecommendation, TrendItem
from app.schemas.trends import TrendFeedCollect, TrendItemRead, TrendRecommendationRead, TrendRecommendationUpdate
from app.services.trend_discovery import collect_rss_feeds

router = APIRouter(tags=["trend discovery"])


def _owned_page(page_id: int, owner_id: str, db: Session) -> Page:
    page = db.scalar(select(Page).where(Page.id == page_id, Page.owner_id == owner_id))
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found.")
    return page


@router.post("/trends/collect")
def collect_trends(payload: TrendFeedCollect, user: CurrentUser, db: Session = Depends(get_db)):
    return {"message": "RSS collection completed.", **collect_rss_feeds(db, user.id, [str(url) for url in payload.feed_urls])}


@router.get("/trends", response_model=list[TrendItemRead])
def list_trends(
    user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return list(db.scalars(
        select(TrendItem).where(TrendItem.owner_id == user.id)
        .order_by(TrendItem.collected_at.desc()).limit(limit)
    ).all())


@router.get("/pages/{page_id}/trends", response_model=list[TrendRecommendationRead])
def list_page_trends(
    page_id: int,
    user: CurrentUser,
    status_filter: str | None = Query(default="suggested", pattern="^(suggested|saved|dismissed|selected)$"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    _owned_page(page_id, user.id, db)
    query = select(PageTrendRecommendation).join(TrendItem).where(
        PageTrendRecommendation.page_id == page_id, TrendItem.owner_id == user.id
    )
    if status_filter:
        query = query.where(PageTrendRecommendation.status == status_filter)
    return list(db.scalars(
        query.order_by(PageTrendRecommendation.score.desc(), PageTrendRecommendation.created_at.desc())
        .limit(limit)
    ).all())


@router.patch("/pages/{page_id}/trends/{recommendation_id}", response_model=TrendRecommendationRead)
def update_page_trend(
    page_id: int,
    recommendation_id: int,
    payload: TrendRecommendationUpdate,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    _owned_page(page_id, user.id, db)
    rec = db.scalar(
        select(PageTrendRecommendation).join(TrendItem).where(
            PageTrendRecommendation.id == recommendation_id,
            PageTrendRecommendation.page_id == page_id,
            TrendItem.owner_id == user.id,
        )
    )
    if rec is None:
        raise HTTPException(status_code=404, detail="Trend recommendation not found.")
    rec.status = payload.status
    db.commit()
    db.refresh(rec)
    return rec
