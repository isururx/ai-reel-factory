from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.database.session import get_db
from app.models.page import Page, PageProfile
from app.schemas.pages import PageCreate, PageProfileRead, PageProfileUpsert, PageRead, PageUpdate

router = APIRouter(prefix="/pages", tags=["pages"])


def owned_page(page_id: int, owner_id: str, db: Session) -> Page:
    page = db.scalar(select(Page).where(Page.id == page_id, Page.owner_id == owner_id))
    if page is None:
        # Return 404 for both missing and foreign-owned IDs to avoid leaking records.
        raise HTTPException(status_code=404, detail="Page not found.")
    return page


@router.post("", response_model=PageRead, status_code=status.HTTP_201_CREATED)
def create_page(payload: PageCreate, user: CurrentUser, db: Session = Depends(get_db)):
    page = Page(**payload.model_dump(), owner_id=user.id)
    db.add(page)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A page with this external ID already exists.")
    db.refresh(page)
    return page


@router.get("", response_model=list[PageRead])
def list_pages(user: CurrentUser, db: Session = Depends(get_db)):
    return list(
        db.scalars(select(Page).where(Page.owner_id == user.id).order_by(Page.id)).all()
    )


@router.get("/{page_id}", response_model=PageRead)
def get_page(page_id: int, user: CurrentUser, db: Session = Depends(get_db)):
    return owned_page(page_id, user.id, db)


@router.patch("/{page_id}", response_model=PageRead)
def update_page(
    page_id: int, payload: PageUpdate, user: CurrentUser, db: Session = Depends(get_db)
):
    page = owned_page(page_id, user.id, db)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Provide at least one field to update.")
    for key, value in changes.items():
        setattr(page, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A page with this external ID already exists.")
    db.refresh(page)
    return page


@router.delete("/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_page(page_id: int, user: CurrentUser, db: Session = Depends(get_db)):
    page = owned_page(page_id, user.id, db)
    db.delete(page)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{page_id}/profile", response_model=PageProfileRead)
def upsert_page_profile(
    page_id: int, payload: PageProfileUpsert, user: CurrentUser, db: Session = Depends(get_db)
):
    owned_page(page_id, user.id, db)
    profile = db.scalar(select(PageProfile).where(PageProfile.page_id == page_id))
    if profile is None:
        profile = PageProfile(page_id=page_id, **payload.model_dump())
        db.add(profile)
    else:
        for key, value in payload.model_dump().items():
            setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/{page_id}/profile", response_model=PageProfileRead)
def get_page_profile(page_id: int, user: CurrentUser, db: Session = Depends(get_db)):
    owned_page(page_id, user.id, db)
    profile = db.scalar(select(PageProfile).where(PageProfile.page_id == page_id))
    if profile is None:
        raise HTTPException(status_code=404, detail="Page profile not found.")
    return profile
