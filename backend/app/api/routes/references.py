from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.database.session import get_db
from app.models.page import Page
from app.models.reference import ReferencePage
from app.schemas.references import ReferencePageCreate, ReferencePageRead, ReferencePageUpdate

router = APIRouter(prefix="/pages/{page_id}/references", tags=["reference intelligence"])


def _owned_page(page_id: int, owner_id: str, db: Session) -> Page:
    page = db.scalar(select(Page).where(Page.id == page_id, Page.owner_id == owner_id))
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found.")
    return page


@router.post("", response_model=ReferencePageRead, status_code=status.HTTP_201_CREATED)
def add_reference_page(
    page_id: int,
    payload: ReferencePageCreate,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    _owned_page(page_id, user.id, db)
    reference = ReferencePage(
        owner_id=user.id,
        page_id=page_id,
        platform="facebook",
        source_url=payload.source_url,
        normalized_url=payload.source_url,
        display_name=payload.display_name,
        notes=payload.notes,
        status="active",
    )
    db.add(reference)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This reference Page is already saved for this workspace.")
    db.refresh(reference)
    return reference


@router.get("", response_model=list[ReferencePageRead])
def list_reference_pages(
    page_id: int,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    _owned_page(page_id, user.id, db)
    return list(db.scalars(
        select(ReferencePage)
        .where(ReferencePage.owner_id == user.id, ReferencePage.page_id == page_id)
        .order_by(ReferencePage.created_at.desc())
    ).all())


@router.patch("/{reference_id}", response_model=ReferencePageRead)
def update_reference_page(
    page_id: int,
    reference_id: int,
    payload: ReferencePageUpdate,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    _owned_page(page_id, user.id, db)
    reference = db.scalar(select(ReferencePage).where(
        ReferencePage.id == reference_id,
        ReferencePage.owner_id == user.id,
        ReferencePage.page_id == page_id,
    ))
    if reference is None:
        raise HTTPException(status_code=404, detail="Reference Page not found.")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Provide at least one field to update.")
    for key, value in changes.items():
        setattr(reference, key, value)
    db.commit()
    db.refresh(reference)
    return reference


@router.delete("/{reference_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reference_page(
    page_id: int,
    reference_id: int,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    _owned_page(page_id, user.id, db)
    reference = db.scalar(select(ReferencePage).where(
        ReferencePage.id == reference_id,
        ReferencePage.owner_id == user.id,
        ReferencePage.page_id == page_id,
    ))
    if reference is None:
        raise HTTPException(status_code=404, detail="Reference Page not found.")
    db.delete(reference)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
