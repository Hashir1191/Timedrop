from datetime import datetime, timezone
from html import escape

from sqlalchemy.orm import Session

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
    """Create the in-app notification and durable email outbox item atomically."""
    if user_id is None:
        return
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return
    notification = Notification(
        user_id=user_id, parcel_id=parcel_id, event_type=event_type,
        title=title, message=message,
    )
    db.add(notification)
    db.flush()
    db.add(NotificationDelivery(
        notification_id=notification.id,
        channel="email",
        recipient=user.email,
        subject=title,
        body=f"<p>{escape(message)}</p><p>TimeDrop delivery updates</p>",
        idempotency_key=f"notification-email-{notification.id}",
        status="pending",
        next_attempt_at=datetime.now(timezone.utc),
    ))
