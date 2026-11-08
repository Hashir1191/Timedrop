
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Parcel
from app.schemas import (
    ParcelCreate,
    ParcelResponse,
    ParcelStatusUpdate,
)


router = APIRouter(
    prefix="/api/v1/parcels",
    tags=["Parcels"],
)


# 1. Register a new parcel
@router.post(
    "/",
    response_model=ParcelResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_parcel(
    parcel_data: ParcelCreate,
    db: Session = Depends(get_db),
):
    parcel = Parcel(**parcel_data.model_dump())

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


# 2. Get all parcels with pagination
@router.get(
    "/",
    response_model=list[ParcelResponse],
)
def get_parcels(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    statement = (
        select(Parcel)
        .order_by(Parcel.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    parcels = db.scalars(statement).all()

    return parcels


# 3. Get a specific parcel using its ID
@router.get(
    "/{parcel_id}",
    response_model=ParcelResponse,
)
def get_parcel(
    parcel_id: int,
    db: Session = Depends(get_db),
):
    parcel = db.get(Parcel, parcel_id)

    if parcel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parcel not found.",
        )

    return parcel


# 4. Update the status of a parcel
@router.patch(
    "/{parcel_id}/status",
    response_model=ParcelResponse,
)
def update_parcel_status(
    parcel_id: int,
    status_data: ParcelStatusUpdate,
    db: Session = Depends(get_db),
):
    parcel = db.get(Parcel, parcel_id)

    if parcel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parcel not found.",
        )

    parcel.status = status_data.status.value

    db.commit()
    db.refresh(parcel)

    return parcel
