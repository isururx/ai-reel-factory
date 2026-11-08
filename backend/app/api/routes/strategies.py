from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.database.session import get_db
from app.models.page import Page
from app.models.strategy import PageStrategy, StrategyVersion
from app.schemas.strategies import (
    StrategyCreate,
    StrategyRead,
    StrategyUpdate,
    StrategyVersionCreate,
    StrategyVersionRead,
)

router = APIRouter(prefix="/pages/{page_id}/strategies", tags=["strategies"])


def require_owned_page(page_id: int, owner_id: str, db: Session) -> None:
    exists = db.scalar(
        select(Page.id).where(Page.id == page_id, Page.owner_id == owner_id)
    )
    if exists is None:
        raise HTTPException(status_code=404, detail="Page not found.")


def get_page_strategy(page_id: int, strategy_id: int, db: Session) -> PageStrategy:
    strategy = db.scalar(
        select(PageStrategy).where(
            PageStrategy.id == strategy_id,
            PageStrategy.page_id == page_id,
        )
    )
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found for this page.")
    return strategy


@router.post("", response_model=StrategyRead, status_code=status.HTTP_201_CREATED)
def create_strategy(
    page_id: int, payload: StrategyCreate, user: CurrentUser, db: Session = Depends(get_db)
):
    require_owned_page(page_id, user.id, db)
    strategy = PageStrategy(page_id=page_id, name=payload.name, description=payload.description)
    strategy.versions.append(StrategyVersion(version_number=1, configuration=payload.configuration))
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return strategy


@router.get("", response_model=list[StrategyRead])
def list_strategies(page_id: int, user: CurrentUser, db: Session = Depends(get_db)):
    require_owned_page(page_id, user.id, db)
    return list(
        db.scalars(
            select(PageStrategy)
            .where(PageStrategy.page_id == page_id)
            .order_by(PageStrategy.id)
        ).all()
    )


@router.patch("/{strategy_id}", response_model=StrategyRead)
def update_strategy(
    page_id: int,
    strategy_id: int,
    payload: StrategyUpdate,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    require_owned_page(page_id, user.id, db)
    strategy = get_page_strategy(page_id, strategy_id, db)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Provide at least one field to update.")
    for key, value in changes.items():
        setattr(strategy, key, value)
    db.commit()
    db.refresh(strategy)
    return strategy


@router.get("/{strategy_id}/versions", response_model=list[StrategyVersionRead])
def list_strategy_versions(
    page_id: int,
    strategy_id: int,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    require_owned_page(page_id, user.id, db)
    get_page_strategy(page_id, strategy_id, db)
    return list(
        db.scalars(
            select(StrategyVersion)
            .where(StrategyVersion.strategy_id == strategy_id)
            .order_by(StrategyVersion.version_number)
        ).all()
    )


@router.post(
    "/{strategy_id}/versions",
    response_model=StrategyVersionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_strategy_version(
    page_id: int,
    strategy_id: int,
    payload: StrategyVersionCreate,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    require_owned_page(page_id, user.id, db)
    get_page_strategy(page_id, strategy_id, db)
    latest_version = db.scalar(
        select(func.max(StrategyVersion.version_number)).where(
            StrategyVersion.strategy_id == strategy_id
        )
    )
    version = StrategyVersion(
        strategy_id=strategy_id,
        version_number=(latest_version or 0) + 1,
        configuration=payload.configuration,
        status="draft",
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version
