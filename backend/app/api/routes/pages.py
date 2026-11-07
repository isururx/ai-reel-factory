from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.page import Page, PageProfile
from app.schemas.pages import PageCreate, PageProfileRead, PageProfileUpsert, PageRead, PageUpdate

router = APIRouter(prefix="/pages", tags=["pages"])


@router.post("", response_model=PageRead, status_code=status.HTTP_201_CREATED)
def create_page(payload: PageCreate, db: Session = Depends(get_db)):
    page = Page(**payload.model_dump())
    db.add(page)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A page with this external ID already exists.")
    db.refresh(page)
    return page


@router.get("", response_model=list[PageRead])
def list_pages(db: Session = Depends(get_db)):
    return list(db.scalars(select(Page).order_by(Page.id)).all())


@router.get("/{page_id}", response_model=PageRead)
def get_page(page_id: int, db: Session = Depends(get_db)):
    page = db.get(Page, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found.")
    return page


@router.patch("/{page_id}", response_model=PageRead)
def update_page(page_id: int, payload: PageUpdate, db: Session = Depends(get_db)):
    page = db.get(Page, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found.")

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
def delete_page(page_id: int, db: Session = Depends(get_db)):
    page = db.get(Page, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found.")
    db.delete(page)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{page_id}/profile", response_model=PageProfileRead)
def upsert_page_profile(page_id: int, payload: PageProfileUpsert, db: Session = Depends(get_db)):
    if db.get(Page, page_id) is None:
        raise HTTPException(status_code=404, detail="Page not found.")
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
def get_page_profile(page_id: int, db: Session = Depends(get_db)):
    if db.get(Page, page_id) is None:
        raise HTTPException(status_code=404, detail="Page not found.")
    profile = db.scalar(select(PageProfile).where(PageProfile.page_id == page_id))
    if profile is None:
        raise HTTPException(status_code=404, detail="Page profile not found.")
    return profile
