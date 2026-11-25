from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import record_operations_audit
from app.database import get_db
from app.models import MerchantApplication, User
from app.security import get_current_user, hash_password, require_admin

router = APIRouter(prefix="/api/v1/merchant-applications", tags=["Merchant onboarding"])
admin_router = APIRouter(prefix="/api/v1/operations/merchant-applications", tags=["Merchant onboarding"])


class MerchantApplicationCreate(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=12, max_length=128)
    phone_number: str = Field(min_length=10, max_length=16)
    business_name: str = Field(min_length=2, max_length=160)
    business_type: str = Field(min_length=2, max_length=80)
    pickup_address: str = Field(min_length=8, max_length=255)
    pickup_city: str = Field(min_length=2, max_length=100)
    pickup_state: str = Field(min_length=2, max_length=100)
    pickup_pincode: str = Field(pattern=r"^[1-9][0-9]{5}$")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("full_name", "business_name", "business_type", "pickup_address", "pickup_city", "pickup_state")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return " ".join(value.split())


class MerchantApplicationDecision(BaseModel):
    reason: str | None = Field(default=None, min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value else value


def application_payload(application: MerchantApplication) -> dict:
    return {
        "id": application.id,
        "user_id": application.user_id,
        "business_name": application.business_name,
        "business_type": application.business_type,
        "contact_name": application.contact_name,
        "email": application.email,
        "phone_number": application.phone_number,
        "pickup_address": application.pickup_address,
        "pickup_city": application.pickup_city,
        "pickup_state": application.pickup_state,
        "pickup_pincode": application.pickup_pincode,
        "status": application.status,
        "review_note": application.review_note,
        "reviewed_at": application.reviewed_at,
        "created_at": application.created_at,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_merchant_application(data: MerchantApplicationCreate, db: Session = Depends(get_db)):
    email = data.email
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    if db.scalar(select(MerchantApplication.id).where(MerchantApplication.email == email)) is not None:
        raise HTTPException(status_code=409, detail="A merchant application with this email already exists.")

    user = User(
        email=email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        role="customer",
        is_active=False,
        phone_number=data.phone_number,
    )
    db.add(user)
    try:
        db.flush()
        application = MerchantApplication(
            user_id=user.id,
            business_name=data.business_name,
            business_type=data.business_type,
            contact_name=data.full_name,
            email=email,
            phone_number=data.phone_number,
            pickup_address=data.pickup_address,
            pickup_city=data.pickup_city,
            pickup_state=data.pickup_state,
            pickup_pincode=data.pickup_pincode,
            status="pending",
        )
        db.add(application)
        db.commit()
        db.refresh(application)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An application or account with these details already exists.")
    return {"message": "Your merchant application has been submitted for review.", "application": application_payload(application)}


@admin_router.get("")
def list_merchant_applications(
    application_status: str | None = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    allowed = {"pending", "approved", "rejected", "suspended"}
    if application_status and application_status not in allowed:
        raise HTTPException(status_code=422, detail="Unsupported application status.")
    statement = select(MerchantApplication).order_by(MerchantApplication.created_at.desc(), MerchantApplication.id.desc())
    if application_status:
        statement = statement.where(MerchantApplication.status == application_status)
    return [application_payload(item) for item in db.scalars(statement).all()]


@admin_router.post("/{application_id}/approve")
def approve_merchant_application(
    application_id: int,
    data: MerchantApplicationDecision,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    application = db.get(MerchantApplication, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Merchant application not found.")
    if application.status != "pending":
        raise HTTPException(status_code=409, detail="Only pending applications can be approved.")
    user = db.get(User, application.user_id)
    if user is None:
        raise HTTPException(status_code=409, detail="The applicant account could not be found.")
    user.role = "merchant"
    user.is_active = True
    application.status = "approved"
    application.review_note = data.reason
    application.reviewed_by_id = admin.id
    application.reviewed_at = datetime.now(timezone.utc)
    record_operations_audit(db, actor_id=admin.id, action="merchant_application.approved",
        entity_type="merchant_application", entity_id=application.id,
        summary=f"Approved merchant application for {application.business_name}",
        changed_fields=["status", "user.role", "user.is_active"])
    db.commit()
    db.refresh(application)
    return application_payload(application)


@admin_router.post("/{application_id}/reject")
def reject_merchant_application(
    application_id: int,
    data: MerchantApplicationDecision,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    application = db.get(MerchantApplication, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Merchant application not found.")
    if application.status != "pending":
        raise HTTPException(status_code=409, detail="Only pending applications can be rejected.")
    application.status = "rejected"
    application.review_note = data.reason
    application.reviewed_by_id = admin.id
    application.reviewed_at = datetime.now(timezone.utc)
    record_operations_audit(db, actor_id=admin.id, action="merchant_application.rejected",
        entity_type="merchant_application", entity_id=application.id,
        summary=f"Rejected merchant application for {application.business_name}",
        changed_fields=["status", "review_note"])
    db.commit()
    db.refresh(application)
    return application_payload(application)


@admin_router.post("/{application_id}/suspend")
def suspend_merchant(
    application_id: int,
    data: MerchantApplicationDecision,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    application = db.get(MerchantApplication, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Merchant application not found.")
    if application.status != "approved":
        raise HTTPException(status_code=409, detail="Only approved merchants can be suspended.")
    user = db.get(User, application.user_id)
    if user is None:
        raise HTTPException(status_code=409, detail="Merchant account could not be found.")
    user.is_active = False
    application.status = "suspended"
    application.review_note = data.reason
    application.reviewed_by_id = admin.id
    application.reviewed_at = datetime.now(timezone.utc)
    record_operations_audit(db, actor_id=admin.id, action="merchant.suspended",
        entity_type="merchant_application", entity_id=application.id,
        summary=f"Suspended merchant account for {application.business_name}",
        changed_fields=["status", "user.is_active"])
    db.commit()
    db.refresh(application)
    return application_payload(application)


@admin_router.post("/{application_id}/reactivate")
def reactivate_merchant(
    application_id: int,
    data: MerchantApplicationDecision,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    application = db.get(MerchantApplication, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Merchant application not found.")
    if application.status != "suspended":
        raise HTTPException(status_code=409, detail="Only suspended merchants can be reactivated.")
    user = db.get(User, application.user_id)
    if user is None:
        raise HTTPException(status_code=409, detail="Merchant account could not be found.")
    user.role = "merchant"
    user.is_active = True
    application.status = "approved"
    application.review_note = data.reason
    application.reviewed_by_id = admin.id
    application.reviewed_at = datetime.now(timezone.utc)
    record_operations_audit(db, actor_id=admin.id, action="merchant.reactivated",
        entity_type="merchant_application", entity_id=application.id,
        summary=f"Reactivated merchant account for {application.business_name}",
        changed_fields=["status", "user.is_active"])
    db.commit()
    db.refresh(application)
    return application_payload(application)
