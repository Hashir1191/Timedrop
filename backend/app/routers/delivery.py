from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.route_planning import enrich_partner_route
from app.models import DeliveryAssignment, DeliveryBooking, DeliveryEvent, DeliveryPartner, DeliverySlot, Parcel, User
from app.notifications import add_notification
from app.schemas import (
    DeliveryCodeResponse, DeliveryProofSubmit, DeliveryEtaUpdate,
    DeliveryAssignmentCreate, DeliveryAssignmentResponse, DeliveryAssignmentStatusUpdate,
    DeliveryPartnerCreate, DeliveryPartnerResponse, DeliveryEventResponse,
    DeliveryRoutePlanResponse, DeliveryRouteStop,
)
from app.security import get_current_user, hash_password, verify_password, require_admin, require_delivery_partner

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
        delivered_at=assignment.delivered_at,
        estimated_delivery_start=assignment.estimated_delivery_start,
        estimated_delivery_end=assignment.estimated_delivery_end,
        proof_recipient_name=assignment.proof_recipient_name,
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
    add_notification(
        db,
        user_id=parcel.owner_id,
        parcel_id=parcel.id,
        event_type="delivery_partner_assigned",
        title="Delivery partner assigned",
        message=f"A delivery partner has been assigned to parcel {parcel.tracking_number}.",
    )
    add_notification(
        db,
        user_id=user.id,
        parcel_id=parcel.id,
        event_type="new_delivery_assignment",
        title="New delivery assigned",
        message=f"Parcel {parcel.tracking_number} has been assigned to you.",
    )
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


@router.get("/route-plan", response_model=DeliveryRoutePlanResponse)
def generate_route_plan(
    delivery_date: date = Query(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Build a non-binding partner/stop proposal for booked parcels on a delivery date.

    The heuristic balances active workload, groups matching PIN-code prefixes,
    and avoids overlapping delivery-slot commitments. It does not estimate road
    distance, traffic, or turn-by-turn navigation.
    """
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    if delivery_date < today:
        raise HTTPException(status_code=400, detail="Route plans cannot be generated for a past date.")

    parcel_rows = db.execute(
        select(Parcel, DeliveryBooking, DeliverySlot)
        .join(DeliveryBooking, DeliveryBooking.parcel_id == Parcel.id)
        .join(DeliverySlot, DeliverySlot.id == DeliveryBooking.slot_id)
        .where(
            DeliveryBooking.status == "booked",
            DeliverySlot.delivery_date == delivery_date,
            Parcel.status == "scheduled",
        )
    ).all()

    active_rows = db.execute(
        select(DeliveryAssignment, Parcel, DeliverySlot)
        .join(Parcel, Parcel.id == DeliveryAssignment.parcel_id)
        .join(DeliveryBooking, DeliveryBooking.parcel_id == Parcel.id)
        .join(DeliverySlot, DeliverySlot.id == DeliveryBooking.slot_id)
        .where(
            DeliveryAssignment.status.in_(["assigned", "accepted", "out_for_delivery"]),
        )
    ).all()

    active_parcel_ids = {assignment.parcel_id for assignment, _, _ in active_rows}
    candidates = db.execute(
        select(DeliveryPartner, User)
        .join(User, User.id == DeliveryPartner.user_id)
        .where(DeliveryPartner.is_available.is_(True), User.is_active.is_(True))
        .order_by(DeliveryPartner.id)
    ).all()

    partner_state = {}
    for partner, user in candidates:
        partner_state[partner.id] = {
            "name": user.full_name,
            "load": 0,
            "intervals": [],
            "zones": {},
            "planned": [],
        }

    for assignment, parcel, slot in active_rows:
        state = partner_state.get(assignment.partner_id)
        if state is None:
            continue
        state["load"] += 1
        if slot.delivery_date == delivery_date:
            state["intervals"].append((slot.start_time, slot.end_time))
            zone = parcel.pincode[:3]
            state["zones"][zone] = state["zones"].get(zone, 0) + 1

    eligible = [
        (parcel, booking, slot)
        for parcel, booking, slot in parcel_rows
        if parcel.id not in active_parcel_ids
    ]
    eligible.sort(key=lambda row: (
        row[2].start_time, row[0].pincode, row[0].city.lower(),
        row[0].address_line.lower(), row[0].tracking_number,
    ))

    planned_stops = []
    unassigned = []
    for parcel, booking, slot in eligible:
        zone = parcel.pincode[:3]
        options = []
        for partner_id, state in partner_state.items():
            overlaps = any(
                not (slot.end_time <= start or slot.start_time >= end)
                for start, end in state["intervals"]
            )
            if overlaps:
                continue
            zone_count = state["zones"].get(zone, 0)
            score = state["load"] * 10 - zone_count * 4
            options.append((score, state["load"], partner_id, zone_count))

        if not options:
            unassigned.append(DeliveryRouteStop(
                parcel_id=parcel.id, tracking_number=parcel.tracking_number,
                recipient_name=parcel.recipient_name, city=parcel.city,
                state=parcel.state, pincode=parcel.pincode,
                delivery_date=slot.delivery_date, slot_start=slot.start_time,
                slot_end=slot.end_time, suggested_partner_id=None,
                suggested_partner_name=None, route_sequence=None,
                partner_active_jobs=0, zone_key=zone,
                recommendation="No available partner can cover this slot without an overlapping assignment.",
            ))
            continue

        score, load, partner_id, zone_count = min(options)
        state = partner_state[partner_id]
        state["intervals"].append((slot.start_time, slot.end_time))
        state["load"] += 1
        state["zones"][zone] = state["zones"].get(zone, 0) + 1
        state["planned"].append(parcel.id)
        sequence = len(state["planned"])
        rationale = (
            f"Grouped with {zone_count} existing or proposed stop(s) in PIN prefix {zone}; "
            f"{load} active job(s) before this proposal."
            if zone_count else
            f"Lowest available workload ({load} active job(s) before this proposal); no overlapping slot."
        )
        planned_stops.append(DeliveryRouteStop(
            parcel_id=parcel.id, tracking_number=parcel.tracking_number,
            recipient_name=parcel.recipient_name, city=parcel.city,
            state=parcel.state, pincode=parcel.pincode,
            delivery_date=slot.delivery_date, slot_start=slot.start_time,
            slot_end=slot.end_time, suggested_partner_id=partner_id,
            suggested_partner_name=state["name"], route_sequence=sequence,
            partner_active_jobs=load, zone_key=zone, recommendation=rationale,
        ))

    # When enabled, geocode and optimize each partner's stop order using OSRM.
    # Provider failures leave the existing deterministic heuristic untouched.
    optimized_stops = []
    grouped_stops = {}
    for stop in planned_stops:
        grouped_stops.setdefault(stop.suggested_partner_id, []).append(stop)
    for partner_id, partner_stops in grouped_stops.items():
        optimized_stops.extend(enrich_partner_route(db, partner_stops, partner_id))

    stops = optimized_stops + unassigned
    if settings.route_mapping_enabled:
        db.commit()  # Persist successful address geocodes for later previews.
    stops.sort(key=lambda stop: (
        stop.suggested_partner_id is None,
        stop.suggested_partner_id or 0,
        stop.route_sequence or 999999,
        stop.slot_start,
        stop.pincode,
    ))
    return DeliveryRoutePlanResponse(
        delivery_date=delivery_date,
        generated_at=datetime.now(timezone.utc),
        total_unassigned=len(eligible),
        recommended=len(planned_stops),
        unassigned_without_partner=len(unassigned),
        mapping_enabled=settings.route_mapping_enabled,
        routing_provider="nominatim_osrm" if settings.route_mapping_enabled else "pin_prefix_heuristic",
        stops=stops,
    )


@router.get("/my-tracking", response_model=list[DeliveryAssignmentResponse])
def my_delivery_tracking(
    db: Session = Depends(get_db),
    customer: User = Depends(get_current_user),
):
    """Return delivery progress only for parcels owned by the signed-in customer."""
    if customer.role != "customer":
        raise HTTPException(status_code=403, detail="Customer access is required.")
    statement = (
        select(DeliveryAssignment)
        .join(Parcel, Parcel.id == DeliveryAssignment.parcel_id)
        .where(Parcel.owner_id == customer.id)
        .order_by(DeliveryAssignment.updated_at.desc())
    )
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
        "out_for_delivery": {"failed"},
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
    status_messages = {
        "accepted": ("Delivery partner accepted", f"The delivery partner accepted parcel {parcel.tracking_number}."),
        "out_for_delivery": ("Your parcel is out for delivery", f"Parcel {parcel.tracking_number} is on its way to you."),
        "failed": ("Delivery attempt unsuccessful", f"The delivery attempt for parcel {parcel.tracking_number} was unsuccessful. Reason: {data.failure_reason}."),
    }
    title, message = status_messages[data.status.value]
    add_notification(
        db,
        user_id=parcel.owner_id,
        parcel_id=parcel.id,
        event_type=f"delivery_{data.status.value}",
        title=title,
        message=message,
    )
    db.commit()
    db.refresh(assignment)
    return _assignment_response(db, assignment)


@router.patch("/assignments/{assignment_id}/eta", response_model=DeliveryAssignmentResponse)
def update_delivery_eta(
    assignment_id: int,
    data: DeliveryEtaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Allow operations or the assigned partner to publish a customer-visible ETA window."""
    assignment = db.get(DeliveryAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Delivery assignment not found.")
    if current_user.role == "delivery_partner":
        partner = db.scalar(select(DeliveryPartner).where(DeliveryPartner.user_id == current_user.id))
        if partner is None or assignment.partner_id != partner.id:
            raise HTTPException(status_code=404, detail="Delivery assignment not found.")
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only operations or the assigned delivery partner can update ETA.")
    if assignment.status not in {"assigned", "accepted", "out_for_delivery"}:
        raise HTTPException(status_code=409, detail="ETA cannot be changed for a completed or failed delivery.")
    now = datetime.now(timezone.utc)
    start = data.estimated_delivery_start.astimezone(timezone.utc)
    end = data.estimated_delivery_end.astimezone(timezone.utc)
    if end <= now:
        raise HTTPException(status_code=422, detail="ETA window must be in the future.")
    assignment.estimated_delivery_start = start
    assignment.estimated_delivery_end = end
    assignment.updated_at = now
    parcel = db.get(Parcel, assignment.parcel_id)
    db.add(DeliveryEvent(
        assignment_id=assignment.id, parcel_id=parcel.id, actor_id=current_user.id,
        event_type="eta_updated", from_status=assignment.status, to_status=assignment.status,
        note=f"Estimated arrival updated to {start.isoformat()} – {end.isoformat()}.",
    ))
    add_notification(
        db,
        user_id=parcel.owner_id,
        parcel_id=parcel.id,
        event_type="delivery_eta_updated",
        title="Delivery arrival estimate updated",
        message=f"Your parcel {parcel.tracking_number} is now estimated to arrive between {start.strftime('%d %b, %I:%M %p')} and {end.strftime('%I:%M %p')} UTC.",
    )
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


@router.post("/parcels/{parcel_id}/delivery-code", response_model=DeliveryCodeResponse)
def issue_delivery_code(
    parcel_id: int,
    db: Session = Depends(get_db),
    customer: User = Depends(get_current_user),
):
    """Issue a short-lived one-time code to the parcel owner for handover verification."""
    if customer.role != "customer":
        raise HTTPException(status_code=403, detail="Only the parcel owner can request a delivery code.")
    parcel = db.get(Parcel, parcel_id)
    if parcel is None or parcel.owner_id != customer.id:
        raise HTTPException(status_code=404, detail="Parcel not found.")
    assignment = db.scalar(select(DeliveryAssignment).where(DeliveryAssignment.parcel_id == parcel_id))
    if assignment is None or assignment.status != "out_for_delivery":
        raise HTTPException(status_code=409, detail="A delivery code is available only while the parcel is out for delivery.")
    if assignment.delivered_at is not None:
        raise HTTPException(status_code=409, detail="This parcel has already been delivered.")
    code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    assignment.delivery_code_hash = hash_password(code)
    assignment.delivery_code_expires_at = expires_at
    assignment.delivery_code_attempts = 0
    db.add(DeliveryEvent(
        assignment_id=assignment.id, parcel_id=parcel_id, actor_id=customer.id,
        event_type="delivery_code_issued", from_status="out_for_delivery",
        to_status="out_for_delivery", note="A one-time delivery code was issued to the parcel owner.",
    ))
    db.commit()
    return DeliveryCodeResponse(code=code, expires_at=expires_at)


@router.post("/assignments/{assignment_id}/proof", response_model=DeliveryAssignmentResponse)
def confirm_delivery_proof(
    assignment_id: int,
    data: DeliveryProofSubmit,
    db: Session = Depends(get_db),
    partner_user: User = Depends(require_delivery_partner),
):
    """Confirm handover using the parcel owner's unexpired one-time code."""
    partner = db.scalar(select(DeliveryPartner).where(DeliveryPartner.user_id == partner_user.id))
    assignment = db.get(DeliveryAssignment, assignment_id)
    if partner is None or assignment is None or assignment.partner_id != partner.id:
        raise HTTPException(status_code=404, detail="Delivery assignment not found.")
    if assignment.status != "out_for_delivery" or assignment.delivered_at is not None:
        raise HTTPException(status_code=409, detail="Only an active out-for-delivery assignment can be completed.")
    if not assignment.delivery_code_hash or not assignment.delivery_code_expires_at:
        raise HTTPException(status_code=409, detail="Ask the recipient to generate a delivery verification code.")
    now = datetime.now(timezone.utc)
    expires_at = assignment.delivery_code_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if now >= expires_at:
        assignment.delivery_code_hash = None
        assignment.delivery_code_expires_at = None
        assignment.delivery_code_attempts = 0
        db.commit()
        raise HTTPException(status_code=410, detail="The delivery code has expired. Ask the recipient to generate a new one.")
    if assignment.delivery_code_attempts >= 5:
        assignment.delivery_code_hash = None
        assignment.delivery_code_expires_at = None
        assignment.delivery_code_attempts = 0
        db.commit()
        raise HTTPException(status_code=429, detail="Too many incorrect attempts. Ask the recipient to generate a new code.")
    if not verify_password(data.code, assignment.delivery_code_hash):
        assignment.delivery_code_attempts += 1
        if assignment.delivery_code_attempts >= 5:
            assignment.delivery_code_hash = None
            assignment.delivery_code_expires_at = None
            assignment.delivery_code_attempts = 0
        db.commit()
        raise HTTPException(status_code=400, detail="Incorrect delivery verification code.")
    previous_status = assignment.status
    assignment.status = "delivered"
    assignment.delivered_at = now
    assignment.proof_recipient_name = data.recipient_name
    assignment.delivery_code_hash = None
    assignment.delivery_code_expires_at = None
    assignment.delivery_code_attempts = 0
    assignment.updated_at = now
    parcel = db.get(Parcel, assignment.parcel_id)
    parcel.status = "delivered"
    db.add(DeliveryEvent(
        assignment_id=assignment.id, parcel_id=assignment.parcel_id,
        actor_id=partner_user.id, event_type="proof_of_delivery",
        from_status=previous_status, to_status="delivered",
        note=f"Delivery verified. Received by {data.recipient_name}.",
    ))
    add_notification(
        db,
        user_id=parcel.owner_id,
        parcel_id=parcel.id,
        event_type="delivery_completed",
        title="Parcel delivered",
        message=f"Parcel {parcel.tracking_number} was successfully delivered and received by {data.recipient_name}.",
    )
    db.commit()
    db.refresh(assignment)
    return _assignment_response(db, assignment)
