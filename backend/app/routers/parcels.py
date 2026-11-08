from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Parcel, User
from app.schemas import ParcelCreate, ParcelResponse, ParcelStatusUpdate
from app.security import get_current_user, require_admin

router = APIRouter(prefix="/api/v1/parcels", tags=["Parcels"])


def _get_accessible_parcel(db: Session, parcel_id: int, user: User) -> Parcel:
    parcel = db.get(Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcel not found.")
    if user.role != "admin" and parcel.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Parcel not found.")
    return parcel


@router.post("/", response_model=ParcelResponse, status_code=status.HTTP_201_CREATED)
def create_parcel(
    parcel_data: ParcelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    parcel = Parcel(**parcel_data.model_dump(), owner_id=current_user.id)
    db.add(parcel)
    try:
        db.commit()
        db.refresh(parcel)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A parcel with this tracking number already exists.",
        )
    return parcel


@router.get("/", response_model=list[ParcelResponse])
def get_parcels(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(Parcel).order_by(Parcel.created_at.desc()).offset(skip).limit(limit)
    if current_user.role != "admin":
        statement = statement.where(Parcel.owner_id == current_user.id)
    return db.scalars(statement).all()


@router.get("/{parcel_id}", response_model=ParcelResponse)
def get_parcel(
    parcel_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_accessible_parcel(db, parcel_id, current_user)


@router.patch("/{parcel_id}/status", response_model=ParcelResponse)
def update_parcel_status(
    parcel_id: int,
    status_data: ParcelStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    parcel = db.get(Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcel not found.")

    parcel.status = status_data.status.value
    db.commit()
    db.refresh(parcel)
    return parcel
