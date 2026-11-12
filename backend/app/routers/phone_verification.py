from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import PhoneVerificationCode, User
from app.schemas import PhoneVerificationRequest, PhoneVerificationSubmit, PhoneVerificationStatus, SmsConsentUpdate
from app.security import get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/v1/phone-verification", tags=["Phone verification and SMS consent"])


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _eligible(user: User) -> None:
    if user.role not in {"customer", "delivery_partner"}:
        raise HTTPException(status_code=403, detail="Phone verification is available to customer and delivery partner accounts.")


@router.get("/me", response_model=PhoneVerificationStatus)
def get_phone_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _eligible(user)
    return PhoneVerificationStatus(
        phone_number=user.phone_number,
        phone_verified=user.phone_verified_at is not None,
        sms_notifications_consent=user.sms_consent_at is not None,
    )


@router.post("/request", status_code=status.HTTP_202_ACCEPTED)
def request_phone_code(
    data: PhoneVerificationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _eligible(user)
    # Real SMS is intentionally unavailable until MSG91 credentials and approved DLT
    # Flow/header/template configuration are supplied. Never pretend an SMS was sent.
    if settings.app_env.lower() == "production":
        raise HTTPException(status_code=503, detail="Phone OTP delivery is not configured. SMS verification is unavailable until the approved MSG91/DLT integration is enabled.")
    if not settings.phone_otp_expose_in_development:
        raise HTTPException(status_code=503, detail="Development OTP exposure is disabled and no SMS provider is configured.")

    now = datetime.now(timezone.utc)
    recent_count = db.scalar(
        select(func.count(PhoneVerificationCode.id)).where(
            PhoneVerificationCode.user_id == user.id,
            PhoneVerificationCode.created_at >= now - timedelta(minutes=15),
        )
    ) or 0
    if recent_count >= 3:
        raise HTTPException(status_code=429, detail="Too many OTP requests. Try again after 15 minutes.")

    existing = db.scalar(select(User).where(User.phone_number == data.phone_number, User.id != user.id))
    if existing is not None:
        raise HTTPException(status_code=409, detail="This phone number is already linked to another account.")

    user.phone_number = data.phone_number
    user.phone_verified_at = None
    user.sms_consent_at = None
    # Invalidate previous unused challenges for this account.
    pending = db.scalars(
        select(PhoneVerificationCode).where(
            PhoneVerificationCode.user_id == user.id,
            PhoneVerificationCode.consumed_at.is_(None),
        )
    ).all()
    for challenge in pending:
        challenge.consumed_at = now

    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = PhoneVerificationCode(
        user_id=user.id,
        phone_number=data.phone_number,
        code_hash=hash_password(code),
        expires_at=now + timedelta(minutes=settings.phone_otp_expire_minutes),
        attempts=0,
    )
    db.add(challenge)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This phone number is already linked to another account.")

    # Development-only convenience. This response field is never returned in production.
    return {
        "message": "Development verification code generated. No SMS was sent.",
        "phone_number": data.phone_number,
        "expires_in_seconds": settings.phone_otp_expire_minutes * 60,
        "development_code": code,
    }


@router.post("/verify", response_model=PhoneVerificationStatus)
def verify_phone_code(
    data: PhoneVerificationSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _eligible(user)
    if not user.phone_number:
        raise HTTPException(status_code=409, detail="Request a verification code first.")
    challenge = db.scalar(
        select(PhoneVerificationCode)
        .where(
            PhoneVerificationCode.user_id == user.id,
            PhoneVerificationCode.phone_number == user.phone_number,
            PhoneVerificationCode.consumed_at.is_(None),
        )
        .order_by(PhoneVerificationCode.created_at.desc(), PhoneVerificationCode.id.desc())
    )
    if challenge is None:
        raise HTTPException(status_code=410, detail="No active verification code. Request a new code.")
    now = datetime.now(timezone.utc)
    if now >= _utc(challenge.expires_at):
        challenge.consumed_at = now
        db.commit()
        raise HTTPException(status_code=410, detail="Verification code expired. Request a new code.")
    if challenge.attempts >= settings.phone_otp_max_attempts:
        challenge.consumed_at = now
        db.commit()
        raise HTTPException(status_code=429, detail="Too many incorrect attempts. Request a new code.")
    if not verify_password(data.code, challenge.code_hash):
        challenge.attempts += 1
        if challenge.attempts >= settings.phone_otp_max_attempts:
            challenge.consumed_at = now
        db.commit()
        raise HTTPException(status_code=400, detail="Incorrect verification code.")
    challenge.consumed_at = now
    user.phone_verified_at = now
    user.sms_consent_at = None
    db.commit()
    db.refresh(user)
    return PhoneVerificationStatus(
        phone_number=user.phone_number,
        phone_verified=True,
        sms_notifications_consent=False,
    )


@router.put("/sms-consent", response_model=PhoneVerificationStatus)
def update_sms_consent(
    data: SmsConsentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _eligible(user)
    if data.enabled and (not user.phone_number or user.phone_verified_at is None):
        raise HTTPException(status_code=409, detail="Verify your phone number before enabling SMS notifications.")
    user.sms_consent_at = datetime.now(timezone.utc) if data.enabled else None
    db.commit()
    db.refresh(user)
    return PhoneVerificationStatus(
        phone_number=user.phone_number,
        phone_verified=user.phone_verified_at is not None,
        sms_notifications_consent=user.sms_consent_at is not None,
    )
