"""Standalone durable notification outbox worker."""
from datetime import datetime, timedelta, timezone
import logging
import time

import httpx
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import NotificationDelivery
from app.providers.msg91 import send_transactional_sms

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("timedrop.notification_worker")


def _claim_one():
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        # Recover work abandoned by a worker that crashed after claiming it.
        stale = db.scalars(select(NotificationDelivery).where(
            NotificationDelivery.status == "processing",
            NotificationDelivery.locked_at < now - timedelta(minutes=5),
        )).all()
        for item in stale:
            item.status = "pending"
            item.locked_at = None
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
                item.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=min(300, 2 ** item.attempts * 5))
            logger.warning("Notification delivery %s failed (attempt %s): %s", item.id, item.attempts, exc)
        db.commit()
    return True


def main() -> None:
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
