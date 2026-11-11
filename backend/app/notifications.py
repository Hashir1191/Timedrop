from sqlalchemy.orm import Session

from app.models import Notification


def add_notification(
    db: Session,
    *,
    user_id: int | None,
    event_type: str,
    title: str,
    message: str,
    parcel_id: int | None = None,
) -> None:
    """Queue an in-app notification in the caller's transaction.

    The caller owns commit/rollback so a notification cannot be persisted for
    a business operation that later fails.
    """
    if user_id is None:
        return
    db.add(
        Notification(
            user_id=user_id,
            parcel_id=parcel_id,
            event_type=event_type,
            title=title,
            message=message,
        )
    )
