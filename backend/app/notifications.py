from datetime import datetime, timezone
from html import escape

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Notification, NotificationDelivery, User


def add_notification(
    db: Session,
    *,
    user_id: int | None,
    event_type: str,
    title: str,
    message: str,
    parcel_id: int | None = None,
) -> None:
    """Create in-app and eligible external notification jobs atomically."""
    if user_id is None:
        return
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return
    notification = Notification(
        user_id=user_id,
        parcel_id=parcel_id,
        event_type=event_type,
        title=title,
        message=message,
    )
    db.add(notification)
    db.flush()
    now = datetime.now(timezone.utc)

    # Email is queued only when the provider is configured at event creation time.
    if settings.resend_api_key:
        db.add(NotificationDelivery(
            notification_id=notification.id,
            channel="email",
            recipient=user.email,
            subject=title,
            body=f"<p>{escape(message)}</p><p>TimeDrop delivery updates</p>",
            idempotency_key=f"notification-email-{notification.id}",
            status="pending",
            next_attempt_at=now,
        ))

    # Never use parcel/partner contact fields for SMS. Only the account-owned,
    # verified number with an explicit active consent timestamp is eligible.
    if (
        settings.sms_notifications_enabled
        and settings.msg91_auth_key
        and settings.msg91_flow_template_id
        and user.phone_number
        and user.phone_verified_at is not None
        and user.sms_consent_at is not None
    ):
        db.add(NotificationDelivery(
            notification_id=notification.id,
            channel="sms",
            recipient=user.phone_number,
            subject=title,
            body=message,
            idempotency_key=f"notification-sms-{notification.id}",
            status="pending",
            next_attempt_at=now,
        ))
