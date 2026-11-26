from datetime import timezone
from hashlib import sha256
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.documents import build_delivery_proof, build_parcel_receipt, create_parcel_registration_receipt
from app.models import DeliveryAssignment, DeliveryBooking, DeliveryEvent, DeliverySlot, Parcel, ParcelCustodyEvent, ParcelDocument, ServiceablePincode, User
from app.schemas import BulkParcelCreate, ParcelCreate, ParcelResponse, ParcelStatusUpdate, ParcelTimelineEvent
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
    service_area = db.scalar(
        select(ServiceablePincode).where(
            ServiceablePincode.pincode == parcel_data.pincode,
            ServiceablePincode.is_active.is_(True),
        )
    )
    if service_area is None:
        raise HTTPException(
            status_code=409,
            detail=f"TimeDrop does not currently serve PIN code {parcel_data.pincode}. Please choose a supported delivery area.",
        )
    parcel = Parcel(**parcel_data.model_dump(), owner_id=current_user.id)
    db.add(parcel)
    try:
        db.flush()
        create_parcel_registration_receipt(db, parcel, current_user.id)
        db.commit()
        db.refresh(parcel)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A parcel with this tracking number already exists.",
        )
    return parcel


@router.post("/bulk", response_model=list[ParcelResponse], status_code=status.HTTP_201_CREATED)
def create_merchant_parcels_bulk(
    payload: BulkParcelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create up to 50 merchant-owned shipments atomically."""
    if current_user.role != "merchant":
        raise HTTPException(status_code=403, detail="Bulk shipment creation is available to approved merchants only.")
    parcels_data = payload.parcels
    tracking_numbers = [item.tracking_number.strip() for item in parcels_data]
    if len(set(tracking_numbers)) != len(tracking_numbers):
        raise HTTPException(status_code=409, detail="The upload contains duplicate tracking numbers.")
    existing = set(db.scalars(select(Parcel.tracking_number).where(Parcel.tracking_number.in_(tracking_numbers))).all())
    if existing:
        raise HTTPException(status_code=409, detail=f"Tracking numbers already registered: {', '.join(sorted(existing))}")
    pincodes = {item.pincode for item in parcels_data}
    serviceable = set(db.scalars(select(ServiceablePincode.pincode).where(
        ServiceablePincode.pincode.in_(pincodes), ServiceablePincode.is_active.is_(True)
    )).all())
    unsupported = sorted(pincodes - serviceable)
    if unsupported:
        raise HTTPException(status_code=409, detail=f"These destination PIN codes are not currently serviceable: {', '.join(unsupported)}. No shipments were created.")
    created: list[Parcel] = []
    try:
        for item in parcels_data:
            parcel = Parcel(**item.model_dump(), owner_id=current_user.id)
            db.add(parcel)
            db.flush()
            create_parcel_registration_receipt(db, parcel, current_user.id)
            created.append(parcel)
        db.commit()
        for parcel in created:
            db.refresh(parcel)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A tracking number conflicts with an existing shipment. No shipments were created.")
    return created


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


@router.get("/{parcel_id}/receipt.pdf")
def download_parcel_receipt(
    parcel_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download the automatically issued, verifiable parcel registration receipt."""
    parcel = _get_accessible_parcel(db, parcel_id, current_user)
    document = db.scalar(
        select(ParcelDocument)
        .where(
            ParcelDocument.parcel_id == parcel.id,
            ParcelDocument.document_type == "parcel_registration",
        )
        .order_by(ParcelDocument.created_at.desc(), ParcelDocument.id.desc())
        .limit(1)
    )
    if document is None:
        raise HTTPException(status_code=404, detail="A registration receipt is not available for this parcel.")

    # Upgrade previously issued/stored receipts when downloaded. Older versions
    # persisted their PDF bytes, so changing the PDF builder alone did not update
    # receipts that already existed in the database. Preserve the original
    # document number, verification code, issuer and issue timestamp.
    issued_at = document.created_at
    if issued_at.tzinfo is None:
        issued_at = issued_at.replace(tzinfo=timezone.utc)
    latest_pdf = build_parcel_receipt(
        parcel,
        document.document_number,
        document.verification_code,
        issued_at,
    )
    latest_hash = sha256(latest_pdf).hexdigest()
    if latest_hash != document.sha256 or latest_pdf != document.pdf_content:
        document.pdf_content = latest_pdf
        document.sha256 = latest_hash
        db.commit()

    safe_tracking = "".join(character for character in parcel.tracking_number if character.isalnum() or character in "-_")
    return Response(
        content=document.pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="TimeDrop-{safe_tracking}-receipt.pdf"',
            "X-Document-Number": document.document_number,
            "X-Document-SHA256": document.sha256,
        },
    )


@router.get("/{parcel_id}/proof-of-delivery.pdf")
def download_proof_of_delivery(
    parcel_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download a proof-of-delivery document only after verified delivery is recorded."""
    parcel = _get_accessible_parcel(db, parcel_id, current_user)
    assignment = db.scalar(
        select(DeliveryAssignment).where(DeliveryAssignment.parcel_id == parcel.id)
    )
    if (
        assignment is None
        or assignment.status != "delivered"
        or assignment.delivered_at is None
        or not assignment.proof_recipient_name
    ):
        raise HTTPException(status_code=409, detail="Proof of delivery is available only after a verified delivery is completed.")

    delivery_event = db.scalar(
        select(DeliveryEvent)
        .where(
            DeliveryEvent.assignment_id == assignment.id,
            DeliveryEvent.event_type == "proof_of_delivery",
            DeliveryEvent.to_status == "delivered",
        )
        .order_by(DeliveryEvent.created_at.desc(), DeliveryEvent.id.desc())
        .limit(1)
    )
    if delivery_event is None:
        raise HTTPException(status_code=409, detail="The verified delivery event is missing; a proof document cannot be issued.")

    document = db.scalar(
        select(ParcelDocument)
        .where(
            ParcelDocument.parcel_id == parcel.id,
            ParcelDocument.document_type == "proof_of_delivery",
        )
        .order_by(ParcelDocument.created_at.desc(), ParcelDocument.id.desc())
        .limit(1)
    )
    if document is None:
        issued_at = datetime.now(timezone.utc)
        document_number = "TD-POD-" + secrets.token_hex(4).upper()
        verification_code = "TDV-" + secrets.token_hex(16).upper()
        content = build_delivery_proof(
            parcel, assignment, delivery_event, document_number, verification_code, issued_at
        )
        document = ParcelDocument(
            parcel_id=parcel.id,
            document_type="proof_of_delivery",
            document_number=document_number,
            verification_code=verification_code,
            sha256=sha256(content).hexdigest(),
            pdf_content=content,
            generated_by_id=current_user.id,
            created_at=issued_at,
        )
        db.add(document)
        db.commit()
        db.refresh(document)

    safe_tracking = "".join(character for character in parcel.tracking_number if character.isalnum() or character in "-_")
    return Response(
        content=document.pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="TimeDrop-{safe_tracking}-proof-of-delivery.pdf"',
            "X-Document-Number": document.document_number,
            "X-Document-SHA256": document.sha256,
        },
    )


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
            "handover_signed": "Delivery partner signed parcel handover",
        }
        for event in delivery_events:
            event_status = event.event_type if event.event_type in {"eta_updated", "handover_signed"} else event.to_status
            title = titles.get(event_status, titles.get(event.event_type, "Delivery progress updated"))
            descriptions = {
                "assigned": "A delivery partner has been assigned to your parcel.",
                "handover_signed": "Your delivery partner acknowledged physical receipt of the parcel from operations.",
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
