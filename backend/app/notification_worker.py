"""Standalone durable notification outbox worker."""
from datetime import datetime, timedelta, timezone
import logging
import time

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Notification, NotificationDelivery, User
from app.providers.msg91 import send_transactional_sms

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("timedrop.notification_worker")


def _retry_delay_seconds(attempts: int) -> int:
    """Return capped exponential backoff for the next delivery attempt."""
    exponent = max(0, attempts - 1)
    delay = settings.notification_retry_base_seconds * (2 ** exponent)
    return min(settings.notification_retry_max_seconds, delay)


def _recover_stale_deliveries(db: Session, now: datetime) -> int:
    """Requeue expired worker leases and count lease losses against retry limits."""
    stale_before = now - timedelta(seconds=settings.notification_delivery_lease_seconds)
    stale = db.scalars(
        select(NotificationDelivery).where(
            NotificationDelivery.status == "processing",
            NotificationDelivery.locked_at.is_not(None),
            NotificationDelivery.locked_at < stale_before,
        )
        .with_for_update(skip_locked=True)
    ).all()

    for item in stale:
        item.attempts += 1
        item.locked_at = None
        item.last_error = "Worker lease expired before delivery was acknowledged."
        if item.attempts >= settings.notification_max_attempts:
            item.status = "failed"
        else:
            item.status = "pending"
            item.next_attempt_at = now + timedelta(seconds=_retry_delay_seconds(item.attempts))

    return len(stale)


def _claim_one():
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        recovered = _recover_stale_deliveries(db, now)
        if recovered:
            logger.warning("Recovered %s notification delivery lease(s)", recovered)
        db.flush()
        item = db.scalar(
            select(NotificationDelivery)
            .where(NotificationDelivery.status == "pending", NotificationDelivery.next_attempt_at <= now)
            .order_by(NotificationDelivery.created_at, NotificationDelivery.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if item is None:
            db.commit()
            return None
        item.status = "processing"
        item.locked_at = now
        db.commit()
        return item.id


def _deliver_email(item: NotificationDelivery) -> str:
    if not settings.resend_api_key:
        raise RuntimeError("RESEND_API_KEY is not configured")
    response = httpx.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": item.idempotency_key,
        },
        json={"from": settings.notification_from_email, "to": [item.recipient], "subject": item.subject, "html": item.body},
        timeout=20.0,
    )
    response.raise_for_status()
    payload = response.json()
    return str(payload.get("id", ""))


def process_one() -> bool:
    item_id = _claim_one()
    if item_id is None:
        return False
    with SessionLocal() as db:
        item = db.get(NotificationDelivery, item_id)
        if item is None:
            return True
        # Consent may be withdrawn after a job was queued. Re-check eligibility
        # immediately before dispatch so queued SMS is cancelled after opt-out.
        if item.channel == "sms":
            notification = db.get(Notification, item.notification_id) if item.notification_id else None
            recipient_user = db.get(User, notification.user_id) if notification else None
            sms_still_allowed = (
                recipient_user is not None
                and recipient_user.is_active
                and settings.sms_notifications_enabled
                and recipient_user.phone_number == item.recipient
                and recipient_user.phone_verified_at is not None
                and recipient_user.sms_consent_at is not None
            )
            if not sms_still_allowed:
                item.status = "cancelled"
                item.last_error = "SMS skipped because the account is no longer verified, active, or opted in."
                item.locked_at = None
                db.commit()
                return True
        try:
            if item.channel == "email":
                provider_id = _deliver_email(item)
            elif item.channel == "sms":
                provider_id = send_transactional_sms(
                    recipient=item.recipient,
                    title=item.subject,
                    message=item.body,
                )
            else:
                raise RuntimeError(f"Unsupported notification channel: {item.channel}")
            item.status = "sent"
            item.sent_at = datetime.now(timezone.utc)
            item.provider_message_id = provider_id or None
            item.last_error = None
            item.locked_at = None
        except Exception as exc:
            item.attempts += 1
            item.last_error = str(exc)[:1000]
            item.locked_at = None
            if item.attempts >= settings.notification_max_attempts:
                item.status = "failed"
            else:
                item.status = "pending"
                item.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=_retry_delay_seconds(item.attempts))
            logger.warning("Notification delivery %s failed (attempt %s): %s", item.id, item.attempts, exc)
        db.commit()
    return True


def main() -> None:
    settings.validate_for_startup()
    logger.info("TimeDrop notification worker started")
    while True:
        try:
            processed = process_one()
        except Exception:
            logger.exception("Notification worker iteration failed")
            processed = False
        if not processed:
            time.sleep(max(1, settings.notification_worker_poll_seconds))


if __name__ == "__main__":
    main()
