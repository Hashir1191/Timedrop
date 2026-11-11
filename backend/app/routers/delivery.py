from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DeliveryAssignment, DeliveryBooking, DeliveryEvent, DeliveryPartner, DeliverySlot, Parcel, User
from app.schemas import (
    DeliveryAssignmentCreate, DeliveryAssignmentResponse, DeliveryAssignmentStatusUpdate,
    DeliveryPartnerCreate, DeliveryPartnerResponse, DeliveryEventResponse,
)
from app.security import get_current_user, hash_password, require_admin, require_delivery_partner

router = APIRouter(prefix="/api/v1/delivery", tags=["Delivery partners"])


def _assignment_response(db: Session, assignment: DeliveryAssignment) -> DeliveryAssignmentResponse:
    parcel = db.get(Parcel, assignment.parcel_id)
    partner = db.get(DeliveryPartner, assignment.partner_id)
    partner_user = db.get(User, partner.user_id)
    booking = db.scalar(select(DeliveryBooking).where(DeliveryBooking.parcel_id == parcel.id))
    slot = db.get(DeliverySlot, booking.slot_id)
    return DeliveryAssignmentResponse(
        id=assignment.id, parcel_id=parcel.id, partner_id=partner.id,
        status=assignment.status, assigned_at=assignment.assigned_at, updated_at=assignment.updated_at,
        tracking_number=parcel.tracking_number, recipient_name=parcel.recipient_name,
        phone=parcel.phone, address_line=parcel.address_line, city=parcel.city,
        state=parcel.state, pincode=parcel.pincode, delivery_date=slot.delivery_date,
        start_time=slot.start_time, end_time=slot.end_time, partner_name=partner_user.full_name,
        failure_reason=assignment.failure_reason,
    )


@router.post("/partners", response_model=DeliveryPartnerResponse, status_code=status.HTTP_201_CREATED)
def create_partner(data: DeliveryPartnerCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if db.scalar(select(User).where(User.email == data.email)) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(email=data.email, full_name=data.full_name.strip(), password_hash=hash_password(data.password), role="delivery_partner")
    partner = DeliveryPartner(phone=data.phone.strip(), vehicle_type=data.vehicle_type.strip())
    db.add(user)
    db.flush()
    partner.user_id = user.id
    db.add(partner)
    try:
        db.commit()
        db.refresh(partner)
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Unable to create partner with these details.")
    return DeliveryPartnerResponse(
        id=partner.id, user_id=user.id, full_name=user.full_name, email=user.email,
        phone=partner.phone, vehicle_type=partner.vehicle_type, is_available=partner.is_available,
        is_active=user.is_active, active_assignments=0,
    )


@router.get("/partners", response_model=list[DeliveryPartnerResponse])
def list_partners(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    rows = db.execute(select(DeliveryPartner, User).join(User, User.id == DeliveryPartner.user_id).order_by(User.full_name)).all()
    result = []
    for partner, user in rows:
        count = db.scalar(select(func.count(DeliveryAssignment.id)).where(
            DeliveryAssignment.partner_id == partner.id,
            DeliveryAssignment.status.in_(["assigned", "accepted", "out_for_delivery"]),
        )) or 0
        result.append(DeliveryPartnerResponse(
            id=partner.id, user_id=user.id, full_name=user.full_name, email=user.email,
            phone=partner.phone, vehicle_type=partner.vehicle_type, is_available=partner.is_available,
            is_active=user.is_active, active_assignments=count,
        ))
    return result


@router.post("/parcels/{parcel_id}/assignments", response_model=DeliveryAssignmentResponse, status_code=status.HTTP_201_CREATED)
def assign_parcel(parcel_id: int, data: DeliveryAssignmentCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    parcel = db.get(Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcel not found.")
    if parcel.status in {"delivered", "failed", "cancelled"}:
        raise HTTPException(status_code=409, detail="A terminal parcel cannot be assigned.")
    booking = db.scalar(select(DeliveryBooking).where(DeliveryBooking.parcel_id == parcel_id, DeliveryBooking.status == "booked"))
    if booking is None:
        raise HTTPException(status_code=409, detail="Book a delivery slot before assigning this parcel.")
    partner = db.get(DeliveryPartner, data.partner_id)
    if partner is None:
        raise HTTPException(status_code=404, detail="Delivery partner not found.")
    user = db.get(User, partner.user_id)
    if not user.is_active or not partner.is_available:
        raise HTTPException(status_code=409, detail="This delivery partner is inactive or unavailable.")
    assignment = db.scalar(select(DeliveryAssignment).where(DeliveryAssignment.parcel_id == parcel_id))
    if assignment and assignment.status in {"assigned", "accepted", "out_for_delivery"}:
        raise HTTPException(status_code=409, detail="This parcel already has an active delivery assignment.")
    if assignment:
        assignment.partner_id = partner.id
        assignment.status = "assigned"
        assignment.assigned_at = datetime.now(timezone.utc)
        assignment.updated_at = datetime.now(timezone.utc)
    else:
        assignment = DeliveryAssignment(parcel_id=parcel_id, partner_id=partner.id)
        db.add(assignment)
    parcel.status = "scheduled"
    db.flush()
    db.add(DeliveryEvent(
        assignment_id=assignment.id, parcel_id=parcel_id, actor_id=admin.id,
        event_type="assigned", from_status=None, to_status="assigned",
    ))
    try:
        db.commit()
        db.refresh(assignment)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This parcel already has a delivery assignment.")
    return _assignment_response(db, assignment)


@router.get("/assignments", response_model=list[DeliveryAssignmentResponse])
def list_assignments(
    assignment_status: str | None = Query(default=None, alias="status", pattern="^(assigned|accepted|out_for_delivery|delivered|failed)$"),
    db: Session = Depends(get_db), admin: User = Depends(require_admin),
):
    statement = select(DeliveryAssignment).order_by(DeliveryAssignment.assigned_at.desc())
    if assignment_status:
        statement = statement.where(DeliveryAssignment.status == assignment_status)
    return [_assignment_response(db, item) for item in db.scalars(statement).all()]


@router.get("/my-assignments", response_model=list[DeliveryAssignmentResponse])
def my_assignments(db: Session = Depends(get_db), partner_user: User = Depends(require_delivery_partner)):
    partner = db.scalar(select(DeliveryPartner).where(DeliveryPartner.user_id == partner_user.id))
    if partner is None:
        raise HTTPException(status_code=403, detail="Delivery partner profile is not configured.")
    statement = select(DeliveryAssignment).where(DeliveryAssignment.partner_id == partner.id).order_by(DeliveryAssignment.assigned_at.desc())
    return [_assignment_response(db, item) for item in db.scalars(statement).all()]


@router.patch("/assignments/{assignment_id}/status", response_model=DeliveryAssignmentResponse)
def update_assignment_status(
    assignment_id: int, data: DeliveryAssignmentStatusUpdate, db: Session = Depends(get_db),
    partner_user: User = Depends(require_delivery_partner),
):
    partner = db.scalar(select(DeliveryPartner).where(DeliveryPartner.user_id == partner_user.id))
    assignment = db.get(DeliveryAssignment, assignment_id)
    if partner is None or assignment is None or assignment.partner_id != partner.id:
        raise HTTPException(status_code=404, detail="Delivery assignment not found.")
    allowed = {
        "assigned": {"accepted", "failed"},
        "accepted": {"out_for_delivery", "failed"},
        "out_for_delivery": {"delivered", "failed"},
    }
    if data.status.value not in allowed.get(assignment.status, set()):
        raise HTTPException(status_code=409, detail=f"Cannot change assignment from {assignment.status} to {data.status.value}.")
    previous_status = assignment.status
    assignment.status = data.status.value
    db.add(DeliveryEvent(
        assignment_id=assignment.id, parcel_id=assignment.parcel_id,
        actor_id=partner_user.id, event_type="status_changed",
        from_status=previous_status, to_status=data.status.value,
        note=data.failure_reason.strip() if data.failure_reason and data.status.value == "failed" else None,
    ))
    assignment.failure_reason = data.failure_reason if data.status.value == "failed" else None
    assignment.updated_at = datetime.now(timezone.utc)
    parcel = db.get(Parcel, assignment.parcel_id)
    parcel.status = data.status.value
    db.commit()
    db.refresh(assignment)
    return _assignment_response(db, assignment)


@router.get("/assignments/{assignment_id}/events", response_model=list[DeliveryEventResponse])
def get_assignment_events(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """History is visible only to operations, the assigned partner, or the parcel owner."""
    assignment = db.get(DeliveryAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Delivery assignment not found.")
    parcel = db.get(Parcel, assignment.parcel_id)
    partner = db.get(DeliveryPartner, assignment.partner_id)
    authorized = (
        current_user.role == "admin"
        or (current_user.role == "customer" and parcel.owner_id == current_user.id)
        or (current_user.role == "delivery_partner" and partner.user_id == current_user.id)
    )
    if not authorized:
        raise HTTPException(status_code=404, detail="Delivery assignment not found.")
    rows = db.execute(
        select(DeliveryEvent, User.full_name)
        .join(User, User.id == DeliveryEvent.actor_id)
        .where(DeliveryEvent.assignment_id == assignment_id)
        .order_by(DeliveryEvent.created_at, DeliveryEvent.id)
    ).all()
    return [
        DeliveryEventResponse(
            id=event.id, assignment_id=event.assignment_id, parcel_id=event.parcel_id,
            actor_id=event.actor_id, actor_name=name, event_type=event.event_type,
            from_status=event.from_status, to_status=event.to_status,
            note=event.note, created_at=event.created_at,
        )
        for event, name in rows
    ]
