from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record_operations_audit
from app.database import get_db
from app.models import NotificationDelivery, User
from app.security import require_admin

router = APIRouter(prefix="/api/v1/operations", tags=["Notification operations"])


class NotificationDeliveryOperationsResponse(BaseModel):
    id: int
    channel: str
    masked_recipient: str
    subject: str
    status: str
    attempts: int
    next_attempt_at: datetime
    locked_at: datetime | None
    sent_at: datetime | None
    provider_message_id: str | None
    last_error: str | None
    created_at: datetime


def _mask_recipient(recipient: str) -> str:
    if "@" in recipient:
        local, domain = recipient.split("@", 1)
        return f"{local[:1]}***@{domain}" if local else f"***@{domain}"
    if len(recipient) <= 4:
        return "****"
    return f"***{recipient[-4:]}"


def _delivery_response(item: NotificationDelivery) -> NotificationDeliveryOperationsResponse:
    return NotificationDeliveryOperationsResponse(
        id=item.id,
        channel=item.channel,
        masked_recipient=_mask_recipient(item.recipient),
        subject=item.subject,
        status=item.status,
        attempts=item.attempts,
        next_attempt_at=item.next_attempt_at,
        locked_at=item.locked_at,
        sent_at=item.sent_at,
        provider_message_id=item.provider_message_id,
        last_error=item.last_error,
        created_at=item.created_at,
    )


@router.get("/notification-deliveries", response_model=list[NotificationDeliveryOperationsResponse])
def list_notification_deliveries(
    status_filter: Literal["pending", "processing", "sent", "failed", "cancelled"] | None = Query(default=None, alias="status"),
    channel: Literal["email", "sms"] | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if skip < 0 or limit < 1 or limit > 200:
        raise HTTPException(status_code=422, detail="Use skip >= 0 and limit between 1 and 200.")
    statement = select(NotificationDelivery).order_by(
        NotificationDelivery.created_at.desc(),
        NotificationDelivery.id.desc(),
    )
    if status_filter:
        statement = statement.where(NotificationDelivery.status == status_filter)
    if channel:
        statement = statement.where(NotificationDelivery.channel == channel)
    items = db.scalars(statement.offset(skip).limit(limit)).all()
    return [_delivery_response(item) for item in items]


@router.post(
    "/notification-deliveries/{delivery_id}/retry",
    response_model=NotificationDeliveryOperationsResponse,
)
def retry_notification_delivery(
    delivery_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    item = db.scalar(
        select(NotificationDelivery)
        .where(NotificationDelivery.id == delivery_id)
        .with_for_update()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Notification delivery not found.")
    if item.status != "failed":
        raise HTTPException(status_code=409, detail="Only failed notification deliveries can be retried.")

    item.status = "pending"
    item.next_attempt_at = datetime.now(timezone.utc)
    item.locked_at = None
    item.last_error = None
    record_operations_audit(
        db,
        actor_id=admin.id,
        action="notification_delivery.requeued",
        entity_type="notification_delivery",
        entity_id=item.id,
        summary=f"Manually requeued failed {item.channel} notification delivery",
        changed_fields=["status", "next_attempt_at", "last_error"],
    )
    db.commit()
    db.refresh(item)
    return _delivery_response(item)
