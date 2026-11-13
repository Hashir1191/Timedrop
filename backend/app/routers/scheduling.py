from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DeliveryAssignment, DeliveryBooking, DeliverySlot, Parcel, User
from app.notifications import add_notification
from app.schemas import (
    BookingCreate,
    BookingResponse,
    AdminBookingResponse,
    DeliverySlotAvailability,
    DeliverySlotCreate,
    ParcelResponse,
    DeliverySlotResponse,
)
from app.security import get_current_user, require_admin

router = APIRouter(prefix="/api/v1/scheduling", tags=["Scheduling"])
INDIA_TZ = ZoneInfo("Asia/Kolkata")


def _local_today() -> date:
    return datetime.now(INDIA_TZ).date()


def _get_accessible_parcel(db: Session, parcel_id: int, user: User) -> Parcel:
    parcel = db.get(Parcel, parcel_id)
    if parcel is None or (user.role != "admin" and parcel.owner_id != user.id):
        raise HTTPException(status_code=404, detail="Parcel not found.")
    return parcel


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


def _ensure_no_active_assignment(db: Session, parcel_id: int) -> None:
    assignment = db.scalar(
        select(DeliveryAssignment).where(
            DeliveryAssignment.parcel_id == parcel_id,
            DeliveryAssignment.status.in_(["assigned", "accepted", "out_for_delivery"]),
        )
    )
    if assignment is not None:
        raise HTTPException(
            status_code=409,
            detail="This parcel has an active delivery assignment. Contact operations to change its booking.",
        )


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
    current_user: User = Depends(require_admin),
):
    if slot_data.delivery_date < _local_today():
        raise HTTPException(status_code=400, detail="Delivery date must be today or in the future.")

    overlapping_slot = db.scalar(
        select(DeliverySlot).where(
            DeliverySlot.delivery_date == slot_data.delivery_date,
            DeliverySlot.is_active.is_(True),
            DeliverySlot.start_time < slot_data.end_time,
            DeliverySlot.end_time > slot_data.start_time,
        )
    )
    if overlapping_slot is not None:
        raise HTTPException(
            status_code=409,
            detail="This delivery window overlaps an existing active slot.",
        )

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
    current_user: User = Depends(get_current_user),
):
    if delivery_date < _local_today():
        raise HTTPException(status_code=400, detail="Cannot view availability for a past date.")

    slots = db.scalars(
        select(DeliverySlot)
        .where(
            DeliverySlot.delivery_date == delivery_date,
            DeliverySlot.is_active.is_(True),
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




@router.get("/bookings", response_model=list[AdminBookingResponse])
def list_bookings(
    booking_status: str | None = Query(default=None, alias="status", pattern="^(booked|cancelled)$"),
    delivery_date: date | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List booking records with their parcel and delivery-slot details for operations."""
    statement = (
        select(DeliveryBooking, Parcel, DeliverySlot)
        .join(Parcel, Parcel.id == DeliveryBooking.parcel_id)
        .join(DeliverySlot, DeliverySlot.id == DeliveryBooking.slot_id)
    )
    if booking_status is not None:
        statement = statement.where(DeliveryBooking.status == booking_status)
    if delivery_date is not None:
        statement = statement.where(DeliverySlot.delivery_date == delivery_date)

    rows = db.execute(
        statement.order_by(
            DeliverySlot.delivery_date.desc(),
            DeliverySlot.start_time,
            DeliveryBooking.id.desc(),
        ).offset(skip).limit(limit)
    ).all()

    return [
        AdminBookingResponse(
            id=booking.id,
            parcel_id=booking.parcel_id,
            slot_id=booking.slot_id,
            status=booking.status,
            booked_at=booking.booked_at,
            updated_at=booking.updated_at,
            parcel=ParcelResponse.model_validate(parcel),
            slot=DeliverySlotResponse.model_validate(slot),
        )
        for booking, parcel, slot in rows
    ]


@router.get("/parcels/{parcel_id}/bookings", response_model=BookingResponse)
def get_parcel_booking(
    parcel_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the current booking for a parcel the caller is allowed to access."""
    _get_accessible_parcel(db, parcel_id, current_user)
    booking = db.scalar(select(DeliveryBooking).where(DeliveryBooking.parcel_id == parcel_id))
    if booking is None or booking.status != "booked":
        raise HTTPException(status_code=404, detail="No active booking exists for this parcel.")
    return _booking_response(db, booking)


@router.post("/parcels/{parcel_id}/bookings", response_model=BookingResponse, status_code=201)
def book_parcel(
    parcel_id: int,
    booking_data: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    parcel = _get_accessible_parcel(db, parcel_id, current_user)
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
        add_notification(
            db,
            user_id=parcel.owner_id,
            parcel_id=parcel.id,
            event_type="booking_created",
            title="Delivery slot booked",
            message=f"Your parcel {parcel.tracking_number} is scheduled for {slot.delivery_date:%d %b %Y}, {slot.start_time:%H:%M}–{slot.end_time:%H:%M}.",
        )
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
    current_user: User = Depends(get_current_user),
):
    parcel = _get_accessible_parcel(db, parcel_id, current_user)
    if parcel.status in {"delivered", "cancelled"}:
        raise HTTPException(status_code=409, detail="This parcel cannot be rescheduled.")

    booking = db.scalar(select(DeliveryBooking).where(DeliveryBooking.parcel_id == parcel_id))
    if booking is None or booking.status != "booked":
        raise HTTPException(status_code=404, detail="No active booking exists for this parcel.")
    _ensure_no_active_assignment(db, parcel_id)
    if booking.slot_id == booking_data.slot_id:
        return _booking_response(db, booking)

    try:
        new_slot = _reserve_capacity(db, booking_data.slot_id)
        old_slot_id = booking.slot_id
        _release_capacity(db, old_slot_id)
        booking.slot_id = new_slot.id
        booking.updated_at = datetime.now(timezone.utc)
        add_notification(
            db,
            user_id=parcel.owner_id,
            parcel_id=parcel.id,
            event_type="booking_rescheduled",
            title="Delivery slot changed",
            message=f"Your parcel {parcel.tracking_number} is now scheduled for {new_slot.delivery_date:%d %b %Y}, {new_slot.start_time:%H:%M}–{new_slot.end_time:%H:%M}.",
        )
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
    current_user: User = Depends(get_current_user),
):
    parcel = _get_accessible_parcel(db, parcel_id, current_user)
    booking = db.scalar(select(DeliveryBooking).where(DeliveryBooking.parcel_id == parcel_id))
    if booking is None or booking.status != "booked":
        raise HTTPException(status_code=404, detail="No active booking exists for this parcel.")
    _ensure_no_active_assignment(db, parcel_id)

    try:
        _release_capacity(db, booking.slot_id)
        booking.status = "cancelled"
        booking.updated_at = datetime.now(timezone.utc)
        parcel.status = "registered"
        add_notification(
            db,
            user_id=parcel.owner_id,
            parcel_id=parcel.id,
            event_type="booking_cancelled",
            title="Delivery booking cancelled",
            message=f"The delivery booking for parcel {parcel.tracking_number} was cancelled.",
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
