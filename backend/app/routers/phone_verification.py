from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import PhoneVerificationCode, User
from app.providers.msg91_otp import send_otp as send_msg91_otp, verify_otp as verify_msg91_otp
from app.schemas import PhoneVerificationRequest, PhoneVerificationSubmit, PhoneVerificationStatus, SmsConsentUpdate
from app.security import get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/v1/phone-verification", tags=["Phone verification and SMS consent"])


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _eligible(user: User) -> None:
    if user.role not in {"customer", "delivery_partner"}:
        raise HTTPException(status_code=403, detail="Phone verification is available to customer and delivery partner accounts.")


def _development_otp_mode() -> bool:
    return settings.app_env.lower() != "production" and settings.phone_otp_expose_in_development


def _check_provider_configuration() -> None:
    if not settings.msg91_auth_key or not settings.msg91_otp_template_id:
        raise HTTPException(status_code=503, detail="Phone verification is not configured. Set the MSG91 auth key and approved OTP template ID, or use the local development OTP mode.")


def _request_code(data: PhoneVerificationRequest, db: Session, user: User):
    _eligible(user)
    development_mode = _development_otp_mode()
    if not development_mode:
        _check_provider_configuration()

    now = datetime.now(timezone.utc)
    recent_count = db.scalar(select(func.count(PhoneVerificationCode.id)).where(
        PhoneVerificationCode.user_id == user.id,
        PhoneVerificationCode.created_at >= now - timedelta(minutes=15),
    )) or 0
    if recent_count >= 3:
        raise HTTPException(status_code=429, detail="Too many OTP requests. Try again after 15 minutes.")

    existing = db.scalar(select(User).where(User.phone_number == data.phone_number, User.id != user.id))
    if existing is not None:
        raise HTTPException(status_code=409, detail="This phone number is already linked to another account.")

    # MSG91 generates and stores the production OTP; TimeDrop never receives it.
    development_code = f"{secrets.randbelow(1_000_000):06d}" if development_mode else None
    try:
        if not development_mode:
            send_msg91_otp(data.phone_number)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to send verification code through the SMS provider. Check provider configuration and try again.") from None

    user.phone_number = data.phone_number
    user.phone_verified_at = None
    user.sms_consent_at = None
    pending = db.scalars(select(PhoneVerificationCode).where(
        PhoneVerificationCode.user_id == user.id,
        PhoneVerificationCode.consumed_at.is_(None),
    )).all()
    for challenge in pending:
        challenge.consumed_at = now

    # In provider mode this opaque value is only a local challenge marker, not the OTP.
    tracking_secret = development_code or secrets.token_urlsafe(32)
    db.add(PhoneVerificationCode(
        user_id=user.id,
        phone_number=data.phone_number,
        code_hash=hash_password(tracking_secret),
        expires_at=now + timedelta(minutes=settings.phone_otp_expire_minutes),
        attempts=0,
    ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This phone number is already linked to another account.")

    if development_mode:
        return {"message": "Development verification code generated. No SMS was sent.", "phone_number": data.phone_number, "expires_in_seconds": settings.phone_otp_expire_minutes * 60, "development_code": development_code, "delivery_mode": "development"}
    return {"message": "Verification code sent. Check your SMS inbox.", "phone_number": data.phone_number, "expires_in_seconds": settings.phone_otp_expire_minutes * 60, "delivery_mode": "msg91"}


@router.get("/me", response_model=PhoneVerificationStatus)
def get_phone_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _eligible(user)
    return PhoneVerificationStatus(phone_number=user.phone_number, phone_verified=user.phone_verified_at is not None, sms_notifications_consent=user.sms_consent_at is not None)


@router.post("/request", status_code=status.HTTP_202_ACCEPTED)
def request_phone_code(data: PhoneVerificationRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _request_code(data, db, user)


@router.post("/resend", status_code=status.HTTP_202_ACCEPTED)
def resend_phone_code(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _eligible(user)
    if not user.phone_number:
        raise HTTPException(status_code=409, detail="Enter your phone number before requesting a code.")
    return _request_code(PhoneVerificationRequest(phone_number=user.phone_number), db, user)


@router.post("/verify", response_model=PhoneVerificationStatus)
def verify_phone_code(data: PhoneVerificationSubmit, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _eligible(user)
    if not user.phone_number:
        raise HTTPException(status_code=409, detail="Request a verification code first.")
    challenge = db.scalar(select(PhoneVerificationCode).where(
        PhoneVerificationCode.user_id == user.id,
        PhoneVerificationCode.phone_number == user.phone_number,
        PhoneVerificationCode.consumed_at.is_(None),
    ).order_by(PhoneVerificationCode.created_at.desc(), PhoneVerificationCode.id.desc()))
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

    try:
        if _development_otp_mode():
            valid_code = verify_password(data.code, challenge.code_hash)
        else:
            _check_provider_configuration()
            valid_code = verify_msg91_otp(user.phone_number, data.code)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to verify the code with the SMS provider. Check provider configuration and try again.") from None

    if not valid_code:
        challenge.attempts += 1
        if challenge.attempts >= settings.phone_otp_max_attempts:
            challenge.consumed_at = now
        db.commit()
        raise HTTPException(status_code=400, detail="Incorrect or expired verification code.")

    challenge.consumed_at = now
    user.phone_verified_at = now
    user.sms_consent_at = None
    db.commit()
    db.refresh(user)
    return PhoneVerificationStatus(phone_number=user.phone_number, phone_verified=True, sms_notifications_consent=False)


@router.put("/sms-consent", response_model=PhoneVerificationStatus)
def update_sms_consent(data: SmsConsentUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _eligible(user)
    if data.enabled and (not user.phone_number or user.phone_verified_at is None):
        raise HTTPException(status_code=409, detail="Verify your phone number before enabling SMS notifications.")
    user.sms_consent_at = datetime.now(timezone.utc) if data.enabled else None
    db.commit()
    db.refresh(user)
    return PhoneVerificationStatus(phone_number=user.phone_number, phone_verified=user.phone_verified_at is not None, sms_notifications_consent=user.sms_consent_at is not None)
