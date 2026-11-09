from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.auth import CurrentUser
from app.database.session import get_db
from app.models.reference import ReferencePage
from app.models.reference_post import ReferencePost, ReferencePostMetric
from app.schemas.reference_posts import ReferencePostRead, ReferenceCollectionResult
from app.services.meta_reference import collect_public_page_posts

router = APIRouter(prefix="/pages/{page_id}/references", tags=["reference intelligence"])


def _reference(page_id: int, reference_id: int, owner_id: str, db: Session) -> ReferencePage:
    item = db.scalar(select(ReferencePage).where(
        ReferencePage.id == reference_id, ReferencePage.page_id == page_id,
        ReferencePage.owner_id == owner_id,
    ))
    if item is None:
        raise HTTPException(status_code=404, detail="Reference Page not found.")
    return item


@router.post("/{reference_id}/collect", response_model=ReferenceCollectionResult)
async def collect_reference_posts(
    page_id: int, reference_id: int, user: CurrentUser,
    limit: int = Query(default=25, ge=1, le=50), db: Session = Depends(get_db),
):
    reference = _reference(page_id, reference_id, user.id, db)
    if reference.status != "active":
        raise HTTPException(status_code=409, detail="Activate this reference Page before collecting posts.")
    incoming = await collect_public_page_posts(reference.normalized_url, limit)
    created = updated = 0
    for item in incoming:
        post = db.scalar(select(ReferencePost).where(
            ReferencePost.reference_page_id == reference.id,
            ReferencePost.external_post_id == item["external_post_id"],
        ))
        if post is None:
            post = ReferencePost(
                owner_id=user.id, reference_page_id=reference.id,
                external_post_id=item["external_post_id"],
            )
            db.add(post)
            db.flush()
            created += 1
        else:
            updated += 1
        post.message = item["message"]
        post.permalink_url = item["permalink_url"]
        post.media_type = item["media_type"]
        post.created_time = item["created_time"]
        post.source_metadata = item["raw"]
        snapshot = ReferencePostMetric(
            owner_id=user.id, post_id=post.id,
            reactions_count=item["reactions_count"],
            comments_count=item["comments_count"],
            shares_count=item["shares_count"],
            available_fields=item["available_fields"],
        )
        db.add(snapshot)
    db.commit()
    return ReferenceCollectionResult(
        reference_page_id=reference.id, status="completed",
        collected_posts=created, updated_posts=updated,
        message="Collection completed. Only fields returned by Meta were stored; unavailable metrics remain null.",
    )


@router.get("/{reference_id}/posts", response_model=list[ReferencePostRead])
def list_reference_posts(
    page_id: int, reference_id: int, user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db),
):
    reference = _reference(page_id, reference_id, user.id, db)
    posts = list(db.scalars(select(ReferencePost).where(
        ReferencePost.reference_page_id == reference.id,
        ReferencePost.owner_id == user.id,
    ).order_by(ReferencePost.created_time.desc()).limit(limit)).all())
    result = []
    scores = []
    rows = []
    for post in posts:
        latest = db.scalar(select(ReferencePostMetric).where(
            ReferencePostMetric.post_id == post.id,
            ReferencePostMetric.owner_id == user.id,
        ).order_by(ReferencePostMetric.captured_at.desc()).limit(1))
        total = None
        if latest:
            values = [latest.reactions_count, latest.comments_count, latest.shares_count]
            known = [value for value in values if value is not None]
            total = sum(known) if known else None
        rows.append((post, latest, total))
        if total is not None:
            scores.append(total)
    baseline = sorted(scores)
    median = baseline[len(baseline)//2] if baseline else 0
    for post, latest, total in rows:
        score = round((total / median) * 100, 1) if total is not None and median > 0 else (100.0 if total == 0 and median == 0 else None)
        result.append(ReferencePostRead(
            id=post.id, external_post_id=post.external_post_id, message=post.message,
            permalink_url=post.permalink_url, media_type=post.media_type, created_time=post.created_time,
            latest_metrics=latest, interaction_count=total, performance_score=score,
        ))
    return result
