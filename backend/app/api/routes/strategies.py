from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.page import Page
from app.models.strategy import PageStrategy, StrategyVersion
from app.schemas.strategies import StrategyCreate, StrategyRead, StrategyVersionRead
router = APIRouter(prefix="/pages/{page_id}/strategies", tags=["strategies"])

def require_page(page_id: int, db: Session):
    if db.get(Page, page_id) is None:
        raise HTTPException(status_code=404, detail="Page not found.")

@router.post("", response_model=StrategyRead, status_code=status.HTTP_201_CREATED)
def create_strategy(page_id: int, payload: StrategyCreate, db: Session = Depends(get_db)):
    require_page(page_id, db)
    strategy = PageStrategy(page_id=page_id, name=payload.name, description=payload.description)
    strategy.versions.append(StrategyVersion(version_number=1, configuration=payload.configuration))
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return strategy

@router.get("", response_model=list[StrategyRead])
def list_strategies(page_id: int, db: Session = Depends(get_db)):
    require_page(page_id, db)
    return list(db.scalars(select(PageStrategy).where(PageStrategy.page_id == page_id).order_by(PageStrategy.id)).all())

@router.get("/{strategy_id}/versions", response_model=list[StrategyVersionRead])
def list_strategy_versions(page_id: int, strategy_id: int, db: Session = Depends(get_db)):
    require_page(page_id, db)
    strategy = db.scalar(select(PageStrategy).where(PageStrategy.id == strategy_id, PageStrategy.page_id == page_id))
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found for this page.")
    return list(db.scalars(select(StrategyVersion).where(StrategyVersion.strategy_id == strategy_id).order_by(StrategyVersion.version_number)).all())
