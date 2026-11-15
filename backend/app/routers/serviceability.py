from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import record_operations_audit
from app.database import get_db
from app.models import ServiceablePincode, User
from app.schemas import (
    ServiceabilityCheckResponse,
    ServiceablePincodeCreate,
    ServiceablePincodeResponse,
    ServiceablePincodeUpdate,
)
from app.security import require_admin

public_router = APIRouter(prefix="/api/v1/serviceability", tags=["Serviceability"])
operations_router = APIRouter(prefix="/api/v1/operations/service-areas", tags=["Operations service areas"])


@public_router.get("/{pincode}", response_model=ServiceabilityCheckResponse)
def check_serviceability(pincode: str, db: Session = Depends(get_db)):
    """Public lookup used before customers register a parcel."""
    if len(pincode) != 6 or not pincode.isdigit() or pincode[0] == "0":
        raise HTTPException(status_code=422, detail="Enter a valid 6-digit Indian PIN code.")
    area = db.scalar(select(ServiceablePincode).where(ServiceablePincode.pincode == pincode))
    if area is None or not area.is_active:
        return ServiceabilityCheckResponse(
            pincode=pincode,
            serviceable=False,
            city=area.city if area else None,
            state=area.state if area else None,
            message="TimeDrop does not currently serve this PIN code.",
        )
    return ServiceabilityCheckResponse(
        pincode=pincode,
        serviceable=True,
        city=area.city,
        state=area.state,
        message=f"Delivery service is available in {area.city}, {area.state}.",
    )


@operations_router.get("/", response_model=list[ServiceablePincodeResponse])
def list_service_areas(
    q: str | None = Query(default=None, max_length=100),
    include_inactive: bool = Query(default=True),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    statement = select(ServiceablePincode).order_by(ServiceablePincode.pincode)
    if not include_inactive:
        statement = statement.where(ServiceablePincode.is_active.is_(True))
    if q and q.strip():
        term = q.strip()
        statement = statement.where(
            ServiceablePincode.pincode.ilike(f"%{term}%")
            | ServiceablePincode.city.ilike(f"%{term}%")
            | ServiceablePincode.state.ilike(f"%{term}%")
        )
    return db.scalars(statement).all()


@operations_router.post("/", response_model=ServiceablePincodeResponse, status_code=status.HTTP_201_CREATED)
def create_service_area(
    data: ServiceablePincodeCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    area = ServiceablePincode(
        pincode=data.pincode,
        city=data.city,
        state=data.state,
    )
    db.add(area)
    try:
        db.flush()
        record_operations_audit(
            db, actor_id=admin.id, action="service_area.created",
            entity_type="service_area", entity_id=area.id,
            summary=f"Added service area for PIN code {area.pincode}",
            changed_fields=["pincode", "city", "state", "is_active"],
        )
        db.commit()
        db.refresh(area)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This PIN code already has a service-area record.")
    return area


@operations_router.patch("/{area_id}", response_model=ServiceablePincodeResponse)
def update_service_area(
    area_id: int,
    data: ServiceablePincodeUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    area = db.get(ServiceablePincode, area_id)
    if area is None:
        raise HTTPException(status_code=404, detail="Service area not found.")
    changes = data.model_dump(exclude_unset=True)
    for field_name, value in changes.items():
        setattr(area, field_name, value)
    try:
        record_operations_audit(
            db, actor_id=admin.id, action="service_area.updated",
            entity_type="service_area", entity_id=area.id,
            summary=f"Updated service area for PIN code {area.pincode}",
            changed_fields=list(changes.keys()),
        )
        db.commit()
        db.refresh(area)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This PIN code already has a service-area record.")
    return area
