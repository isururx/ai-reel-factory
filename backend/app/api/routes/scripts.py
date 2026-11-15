from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.auth import CurrentUser
from app.core.settings import settings
from app.database.session import get_db
from app.models.content import ApprovalEvent, ContentScript, ScriptVersion
from app.models.page import Page, PageProfile
from app.models.strategy import PageStrategy
from app.schemas.scripts import ContentScriptRead, ScriptDecision, ScriptGenerateRequest, ScriptVersionRead, ScriptVersionUpdate
from app.services.script_generation import generate_script

router = APIRouter(tags=["AI script generation"])


def _owned_page(page_id: int, owner_id: str, db: Session) -> Page:
    page = db.scalar(select(Page).where(Page.id == page_id, Page.owner_id == owner_id))
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found.")
    return page


def _owned_script(page_id: int, script_id: int, db: Session) -> ContentScript:
    script = db.scalar(
        select(ContentScript)
        .options(selectinload(ContentScript.versions))
        .where(ContentScript.id == script_id, ContentScript.page_id == page_id)
    )
    if script is None:
        raise HTTPException(status_code=404, detail="Script not found.")
    return script


@router.post(
    "/pages/{page_id}/scripts/generate",
    response_model=ContentScriptRead,
    status_code=status.HTTP_201_CREATED,
)
def generate_script_for_page(
    page_id: int,
    payload: ScriptGenerateRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    _owned_page(page_id, user.id, db)
    profile = db.scalar(select(PageProfile).where(PageProfile.page_id == page_id))
    if profile is None:
        raise HTTPException(status_code=400, detail="Configure this Page profile before generating a script.")

    strategy = db.scalar(
        select(PageStrategy)
        .options(selectinload(PageStrategy.versions))
        .where(PageStrategy.page_id == page_id, PageStrategy.status == "active")
        .order_by(PageStrategy.id.desc())
    )
    strategy_config = {}
    if strategy and strategy.versions:
        active = next((version for version in reversed(strategy.versions) if version.status == "active"), None)
        strategy_config = (active or max(strategy.versions, key=lambda version: version.version_number)).configuration

    context = {
        "profile": {
            "niche": profile.niche,
            "target_audience": profile.target_audience,
            "language": profile.language,
            "tone": profile.tone,
            "preferred_formats": profile.preferred_formats,
            "restricted_topics": profile.restricted_topics,
            "fact_check_level": profile.fact_check_level,
        },
        "strategy": strategy_config,
        "brief": payload.brief,
        "source_url": str(payload.source_url) if payload.source_url else None,
    }
    try:
        item = generate_script(context)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Script generation failed: {exc}") from exc

    script = ContentScript(page_id=page_id, title=item["title"], status="review")
    script.versions.append(
        ScriptVersion(
            version_number=1,
            hook=item["hook"],
            narration=item["narration"],
            caption=item["caption"],
            hashtags=item["hashtags"],
            script_data={
                **item["script_data"],
                "title": item["title"],
                "generation_provider": settings.llm_provider,
                "generation_brief": payload.brief,
            },
        )
    )
    db.add(script)
    db.commit()
    return _owned_script(page_id, script.id, db)


@router.get("/pages/{page_id}/scripts", response_model=list[ContentScriptRead])
def list_scripts(page_id: int, user: CurrentUser, db: Session = Depends(get_db)):
    _owned_page(page_id, user.id, db)
    return list(
        db.scalars(
            select(ContentScript)
            .options(selectinload(ContentScript.versions))
            .where(ContentScript.page_id == page_id)
            .order_by(ContentScript.created_at.desc())
        ).all()
    )


@router.post(
    "/pages/{page_id}/scripts/{script_id}/versions",
    response_model=ScriptVersionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_edited_version(
    page_id: int,
    script_id: int,
    payload: ScriptVersionUpdate,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    _owned_page(page_id, user.id, db)
    script = _owned_script(page_id, script_id, db)
    latest = db.scalar(select(func.max(ScriptVersion.version_number)).where(ScriptVersion.script_id == script_id)) or 0
    previous = max(script.versions, key=lambda version: version.version_number)
    data = dict(previous.script_data or {})
    data["edited_by_human"] = True
    version = ScriptVersion(
        script_id=script_id,
        version_number=latest + 1,
        hook=payload.hook,
        narration=payload.narration,
        caption=payload.caption,
        hashtags=payload.hashtags,
        script_data={**data, "title": payload.title},
    )
    script.title = payload.title
    script.status = "review"
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


@router.post(
    "/pages/{page_id}/scripts/{script_id}/versions/{version_id}/decision",
    response_model=ContentScriptRead,
)
def decide_script(
    page_id: int,
    script_id: int,
    version_id: int,
    payload: ScriptDecision,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    _owned_page(page_id, user.id, db)
    script = _owned_script(page_id, script_id, db)
    version = db.scalar(
        select(ScriptVersion).where(
            ScriptVersion.id == version_id,
            ScriptVersion.script_id == script_id,
        )
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Script version not found.")
    db.add(
        ApprovalEvent(
            script_version_id=version_id,
            decision=payload.decision,
            reviewer=user.email or user.id,
            comments=payload.comments,
        )
    )
    script.status = "approved" if payload.decision == "approved" else "rejected"
    db.commit()
    return _owned_script(page_id, script_id, db)
