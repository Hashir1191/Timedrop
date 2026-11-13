from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DeliveryAssignment, DeliveryPartner, Parcel, ParcelCustodyEvent, User
from app.security import require_admin

router = APIRouter(prefix="/api/v1/operations", tags=["Operations intake and custody"])


class ParcelIntakeCreate(BaseModel):
    tracking_number: str = Field(min_length=3, max_length=64)
    recipient_name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=10, max_length=20)
    address_line: str = Field(min_length=5, max_length=255)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    pincode: str = Field(pattern=r"^[1-9][0-9]{5}$")
    customer_email: str | None = Field(default=None, max_length=255)

    @field_validator("customer_email")
    @classmethod
    def normalize_customer_email(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("A valid customer email address is required.")
        return normalized

    received_from: str = Field(min_length=2, max_length=120)
    package_condition: str = Field(pattern=r"^(intact|damaged|opened)$")
    note: str | None = Field(default=None, max_length=500)


class ParcelIntakeResponse(BaseModel):
    id: int
    tracking_number: str
    recipient_name: str
    city: str
    state: str
    pincode: str
    status: str
    received_from: str
    package_condition: str
    received_at: datetime
    customer_email: str | None = None


class CustodyEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    parcel_id: int
    actor_id: int
    event_type: str
    package_condition: str | None
    received_from: str | None
    handed_to: str | None
    note: str | None
    created_at: datetime


class CustodyReleaseRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class CustodyReturnRequest(BaseModel):
    package_condition: str = Field(pattern=r"^(intact|damaged|opened)$")
    note: str = Field(min_length=3, max_length=500)


def _intake_response(parcel: Parcel, event: ParcelCustodyEvent, owner: User | None):
    return ParcelIntakeResponse(
        id=parcel.id,
        tracking_number=parcel.tracking_number,
        recipient_name=parcel.recipient_name,
        city=parcel.city,
        state=parcel.state,
        pincode=parcel.pincode,
        status=parcel.status,
        received_from=event.received_from or "",
        package_condition=event.package_condition or "unknown",
        received_at=event.created_at,
        customer_email=owner.email if owner else None,
    )


@router.post("/intake", response_model=ParcelIntakeResponse, status_code=status.HTTP_201_CREATED)
def receive_parcel(data: ParcelIntakeCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Register an authorized parcel and record its initial physical receipt."""
    owner = None
    if data.customer_email:
        owner = db.scalar(select(User).where(User.email == str(data.customer_email).strip().lower()))
        if owner is None or owner.role != "customer" or not owner.is_active:
            raise HTTPException(status_code=404, detail="An active customer account with that email was not found.")

    parcel = Parcel(
        tracking_number=data.tracking_number.strip(),
        recipient_name=data.recipient_name.strip(),
        phone=data.phone.strip(),
        address_line=data.address_line.strip(),
        city=data.city.strip(),
        state=data.state.strip(),
        pincode=data.pincode,
        owner_id=owner.id if owner else None,
        status="registered",
    )
    db.add(parcel)
    try:
        db.flush()
        event = ParcelCustodyEvent(
            parcel_id=parcel.id,
            actor_id=admin.id,
            event_type="received",
            package_condition=data.package_condition,
            received_from=data.received_from.strip(),
            note=data.note.strip() if data.note else None,
        )
        db.add(event)
        db.commit()
        db.refresh(parcel)
        db.refresh(event)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A parcel with this tracking number already exists.")
    return _intake_response(parcel, event, owner)


@router.get("/intake", response_model=list[ParcelIntakeResponse])
def list_received_parcels(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """List parcels registered through operations intake, newest receipt first."""
    rows = db.execute(
        select(Parcel, ParcelCustodyEvent, User)
        .join(ParcelCustodyEvent, ParcelCustodyEvent.parcel_id == Parcel.id)
        .outerjoin(User, User.id == Parcel.owner_id)
        .where(ParcelCustodyEvent.event_type == "received")
        .order_by(ParcelCustodyEvent.created_at.desc(), ParcelCustodyEvent.id.desc())
        .limit(100)
    ).all()
    return [_intake_response(parcel, event, owner) for parcel, event, owner in rows]


@router.get("/parcels/{parcel_id}/custody", response_model=list[CustodyEventResponse])
def get_custody_history(parcel_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if db.get(Parcel, parcel_id) is None:
        raise HTTPException(status_code=404, detail="Parcel not found.")
    events = db.scalars(
        select(ParcelCustodyEvent)
        .where(ParcelCustodyEvent.parcel_id == parcel_id)
        .order_by(ParcelCustodyEvent.created_at, ParcelCustodyEvent.id)
    ).all()
    return events


@router.post("/parcels/{parcel_id}/release", response_model=CustodyEventResponse, status_code=status.HTTP_201_CREATED)
def release_parcel(parcel_id: int, data: CustodyReleaseRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Record handover from TimeDrop custody to the assigned delivery partner."""
    parcel = db.get(Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcel not found.")
    latest = db.scalar(
        select(ParcelCustodyEvent)
        .where(ParcelCustodyEvent.parcel_id == parcel_id)
        .order_by(ParcelCustodyEvent.created_at.desc(), ParcelCustodyEvent.id.desc())
        .limit(1)
    )
    if latest is None or latest.event_type not in {"received", "returned"}:
        raise HTTPException(status_code=409, detail="This parcel is not currently recorded as being in TimeDrop custody.")
    assignment = db.scalar(select(DeliveryAssignment).where(DeliveryAssignment.parcel_id == parcel_id))
    if assignment is None or assignment.status != "assigned":
        raise HTTPException(status_code=409, detail="Assign the parcel to a delivery partner before releasing custody.")
    partner = db.get(DeliveryPartner, assignment.partner_id)
    partner_user = db.get(User, partner.user_id) if partner else None
    if partner_user is None:
        raise HTTPException(status_code=409, detail="The assigned delivery partner could not be found.")
    event = ParcelCustodyEvent(
        parcel_id=parcel_id,
        actor_id=admin.id,
        event_type="released",
        handed_to=partner_user.full_name,
        note=data.note.strip() if data.note else "Handed over to the assigned delivery partner.",
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.post("/parcels/{parcel_id}/return", response_model=CustodyEventResponse, status_code=status.HTTP_201_CREATED)
def receive_failed_parcel(
    parcel_id: int,
    data: CustodyReturnRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Record physical return of a failed delivery from its assigned partner to operations."""
    parcel = db.get(Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcel not found.")

    latest = db.scalar(
        select(ParcelCustodyEvent)
        .where(ParcelCustodyEvent.parcel_id == parcel_id)
        .order_by(ParcelCustodyEvent.created_at.desc(), ParcelCustodyEvent.id.desc())
        .limit(1)
    )
    if latest is None or latest.event_type != "released":
        raise HTTPException(status_code=409, detail="The parcel must be recorded as released to a delivery partner before it can be returned.")

    assignment = db.scalar(select(DeliveryAssignment).where(DeliveryAssignment.parcel_id == parcel_id))
    if assignment is None or assignment.status != "failed":
        raise HTTPException(status_code=409, detail="Only a failed delivery can be received back into operations.")

    partner = db.get(DeliveryPartner, assignment.partner_id)
    partner_user = db.get(User, partner.user_id) if partner else None
    if partner_user is None:
        raise HTTPException(status_code=409, detail="The assigned delivery partner could not be found.")

    event = ParcelCustodyEvent(
        parcel_id=parcel_id,
        actor_id=admin.id,
        event_type="returned",
        package_condition=data.package_condition,
        received_from=partner_user.full_name,
        note=data.note.strip(),
    )
    parcel.status = "returned_to_operations"
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
