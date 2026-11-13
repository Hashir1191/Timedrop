from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DeliveryAssignment, DeliveryBooking, DeliveryEvent, DeliverySlot, Parcel, ParcelCustodyEvent, User
from app.schemas import ParcelCreate, ParcelResponse, ParcelStatusUpdate, ParcelTimelineEvent
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


@router.get("/{parcel_id}/timeline", response_model=list[ParcelTimelineEvent])
def get_parcel_timeline(
    parcel_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a customer-safe, chronological history for an owned parcel."""
    parcel = _get_accessible_parcel(db, parcel_id, current_user)
    timeline: list[dict] = [{
        "id": f"parcel-{parcel.id}",
        "event_type": "parcel_registered",
        "title": "Parcel registered",
        "description": "Your parcel was registered with TimeDrop.",
        "status": "registered",
        "created_at": parcel.created_at,
    }]

    booking = db.scalar(select(DeliveryBooking).where(DeliveryBooking.parcel_id == parcel.id))
    if booking is not None:
        slot = db.get(DeliverySlot, booking.slot_id)
        if slot is not None:
            active = booking.status == "booked"
            timeline.append({
                "id": f"booking-{booking.id}",
                "event_type": f"booking_{booking.status}",
                "title": "Delivery slot booked" if active else "Delivery booking cancelled",
                "description": (
                    f"Your delivery is scheduled for {slot.delivery_date:%d %b %Y}, "
                    f"{slot.start_time:%H:%M}–{slot.end_time:%H:%M}."
                    if active else "The previous delivery slot booking was cancelled."
                ),
                "status": booking.status,
                "created_at": booking.updated_at,
            })

    assignment = db.scalar(
        select(DeliveryAssignment).where(DeliveryAssignment.parcel_id == parcel.id)
    )
    if assignment is not None:
        delivery_events = db.scalars(
            select(DeliveryEvent)
            .where(
                DeliveryEvent.parcel_id == parcel.id,
                DeliveryEvent.event_type != "delivery_code_issued",
            )
            .order_by(DeliveryEvent.created_at, DeliveryEvent.id)
        ).all()
        titles = {
            "assigned": "Delivery partner assigned",
            "accepted": "Delivery partner accepted the parcel",
            "out_for_delivery": "Parcel is out for delivery",
            "failed": "Delivery attempt unsuccessful",
            "delivered": "Parcel delivered",
            "eta_updated": "Estimated arrival updated",
        }
        for event in delivery_events:
            event_status = "eta_updated" if event.event_type == "eta_updated" else event.to_status
            title = titles.get(event_status, titles.get(event.event_type, "Delivery progress updated"))
            descriptions = {
                "assigned": "A delivery partner has been assigned to your parcel.",
                "accepted": "The delivery partner has accepted the assignment.",
                "out_for_delivery": "Your parcel is on its way to the delivery address.",
                "failed": "The delivery attempt was unsuccessful. Operations will coordinate the next step.",
                "delivered": "Delivery confirmation has been recorded.",
                "eta_updated": "The estimated arrival window was updated.",
            }
            timeline.append({
                "id": f"delivery-{event.id}",
                "event_type": event.event_type,
                "title": title,
                "description": descriptions.get(event_status, "Your parcel's delivery progress was updated."),
                "status": event_status,
                "created_at": event.created_at,
            })

    custody_events = db.scalars(
        select(ParcelCustodyEvent)
        .where(ParcelCustodyEvent.parcel_id == parcel.id)
        .order_by(ParcelCustodyEvent.created_at, ParcelCustodyEvent.id)
    ).all()
    custody_copy = {
        "received": ("Received by operations", "Your parcel has been received by the TimeDrop operations team."),
        "released": ("Handed to delivery partner", "Your parcel has been handed over to its delivery partner."),
        "returned": ("Returned to operations", "Your parcel has been returned to operations after a delivery attempt."),
    }
    for event in custody_events:
        title, description = custody_copy.get(
            event.event_type,
            ("Parcel custody updated", "The physical handling of your parcel was updated."),
        )
        timeline.append({
            "id": f"custody-{event.id}",
            "event_type": f"custody_{event.event_type}",
            "title": title,
            "description": description,
            "status": event.event_type,
            "created_at": event.created_at,
        })

    def chronological(item: dict):
        value = item["created_at"]
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value

    timeline.sort(key=chronological)
    return timeline
