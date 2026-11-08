from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DeliveryBooking, DeliverySlot, Parcel
from app.schemas import (
    BookingCreate,
    BookingResponse,
    DeliverySlotAvailability,
    DeliverySlotCreate,
)

router = APIRouter(prefix="/api/v1/scheduling", tags=["Scheduling"])
INDIA_TZ = ZoneInfo("Asia/Kolkata")


def _local_today() -> date:
    return datetime.now(INDIA_TZ).date()


def _booking_response(db: Session, booking: DeliveryBooking) -> BookingResponse:
    slot = db.get(DeliverySlot, booking.slot_id)
    return BookingResponse(
        id=booking.id,
        parcel_id=booking.parcel_id,
        slot_id=booking.slot_id,
        delivery_date=slot.delivery_date,
        start_time=slot.start_time,
        end_time=slot.end_time,
        status=booking.status,
        booked_at=booking.booked_at,
        updated_at=booking.updated_at,
    )


def _reserve_capacity(db: Session, slot_id: int) -> DeliverySlot:
    slot = db.get(DeliverySlot, slot_id)
    if slot is None or not slot.is_active:
        raise HTTPException(status_code=404, detail="Delivery slot not found or inactive.")
    if slot.delivery_date < _local_today():
        raise HTTPException(status_code=400, detail="Cannot book a slot in the past.")

    result = db.execute(
        update(DeliverySlot)
        .where(
            DeliverySlot.id == slot_id,
            DeliverySlot.is_active.is_(True),
            DeliverySlot.booked_count < DeliverySlot.capacity,
        )
        .values(booked_count=DeliverySlot.booked_count + 1)
    )
    if result.rowcount != 1:
        raise HTTPException(status_code=409, detail="This delivery slot is fully booked.")
    db.flush()
    db.refresh(slot)
    return slot


def _release_capacity(db: Session, slot_id: int) -> None:
    result = db.execute(
        update(DeliverySlot)
        .where(DeliverySlot.id == slot_id, DeliverySlot.booked_count > 0)
        .values(booked_count=DeliverySlot.booked_count - 1)
    )
    if result.rowcount != 1:
        raise HTTPException(status_code=409, detail="Slot capacity is inconsistent; contact operations.")


@router.post("/slots", status_code=status.HTTP_201_CREATED)
def create_delivery_slot(
    slot_data: DeliverySlotCreate,
    db: Session = Depends(get_db),
):
    if slot_data.delivery_date < _local_today():
        raise HTTPException(status_code=400, detail="Delivery date must be today or in the future.")

    slot = DeliverySlot(**slot_data.model_dump())
    db.add(slot)
    try:
        db.commit()
        db.refresh(slot)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This delivery window already exists.")
    return {
        "id": slot.id,
        "delivery_date": slot.delivery_date,
        "start_time": slot.start_time,
        "end_time": slot.end_time,
        "capacity": slot.capacity,
        "booked_count": slot.booked_count,
        "remaining_capacity": slot.capacity - slot.booked_count,
        "is_active": slot.is_active,
    }


@router.get("/slots", response_model=list[DeliverySlotAvailability])
def get_available_slots(
    delivery_date: date = Query(...),
    db: Session = Depends(get_db),
):
    if delivery_date < _local_today():
        raise HTTPException(status_code=400, detail="Cannot view availability for a past date.")

    slots = db.scalars(
        select(DeliverySlot)
        .where(
            DeliverySlot.delivery_date == delivery_date,
            DeliverySlot.is_active.is_(True),
            DeliverySlot.booked_count < DeliverySlot.capacity,
        )
        .order_by(DeliverySlot.start_time)
    ).all()

    return [
        DeliverySlotAvailability(
            id=slot.id,
            delivery_date=slot.delivery_date,
            start_time=slot.start_time,
            end_time=slot.end_time,
            capacity=slot.capacity,
            booked_count=slot.booked_count,
            remaining_capacity=slot.capacity - slot.booked_count,
        )
        for slot in slots
    ]


@router.post("/parcels/{parcel_id}/bookings", response_model=BookingResponse, status_code=201)
def book_parcel(
    parcel_id: int,
    booking_data: BookingCreate,
    db: Session = Depends(get_db),
):
    parcel = db.get(Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcel not found.")
    if parcel.status in {"delivered", "cancelled"}:
        raise HTTPException(status_code=409, detail="This parcel cannot be scheduled.")

    existing = db.scalar(
        select(DeliveryBooking).where(
            DeliveryBooking.parcel_id == parcel_id,
            DeliveryBooking.status == "booked",
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="This parcel already has an active booking. Use reschedule.")

    try:
        slot = _reserve_capacity(db, booking_data.slot_id)
        booking = db.scalar(select(DeliveryBooking).where(DeliveryBooking.parcel_id == parcel_id))
        if booking is None:
            booking = DeliveryBooking(parcel_id=parcel_id, slot_id=slot.id, status="booked")
            db.add(booking)
        else:
            booking.slot_id = slot.id
            booking.status = "booked"
            booking.updated_at = datetime.now(timezone.utc)
        parcel.status = "scheduled"
        db.commit()
        db.refresh(booking)
        return _booking_response(db, booking)
    except Exception:
        db.rollback()
        raise


@router.patch("/parcels/{parcel_id}/bookings", response_model=BookingResponse)
def reschedule_parcel(
    parcel_id: int,
    booking_data: BookingCreate,
    db: Session = Depends(get_db),
):
    parcel = db.get(Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcel not found.")
    if parcel.status in {"delivered", "cancelled"}:
        raise HTTPException(status_code=409, detail="This parcel cannot be rescheduled.")

    booking = db.scalar(select(DeliveryBooking).where(DeliveryBooking.parcel_id == parcel_id))
    if booking is None or booking.status != "booked":
        raise HTTPException(status_code=404, detail="No active booking exists for this parcel.")
    if booking.slot_id == booking_data.slot_id:
        return _booking_response(db, booking)

    try:
        _reserve_capacity(db, booking_data.slot_id)
        old_slot_id = booking.slot_id
        _release_capacity(db, old_slot_id)
        booking.slot_id = booking_data.slot_id
        booking.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(booking)
        return _booking_response(db, booking)
    except Exception:
        db.rollback()
        raise


@router.delete("/parcels/{parcel_id}/bookings", status_code=204)
def cancel_booking(
    parcel_id: int,
    db: Session = Depends(get_db),
):
    parcel = db.get(Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcel not found.")

    booking = db.scalar(select(DeliveryBooking).where(DeliveryBooking.parcel_id == parcel_id))
    if booking is None or booking.status != "booked":
        raise HTTPException(status_code=404, detail="No active booking exists for this parcel.")

    try:
        _release_capacity(db, booking.slot_id)
        booking.status = "cancelled"
        booking.updated_at = datetime.now(timezone.utc)
        parcel.status = "registered"
        db.commit()
    except Exception:
        db.rollback()
        raise
