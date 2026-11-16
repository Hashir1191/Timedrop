from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import NotificationDelivery, User, WorkerHeartbeat
from app.security import require_admin

router = APIRouter(prefix="/api/v1/operations", tags=["System health"])


class OperationsSystemHealthResponse(BaseModel):
    database_status: Literal["ok"]
    notification_worker_status: Literal["healthy", "stale", "not_seen"]
    worker_last_seen_at: datetime | None
    worker_age_seconds: int | None
    worker_stale_after_seconds: int
    notification_queue: dict[str, int]
    checked_at: datetime


@router.get("/system-health", response_model=OperationsSystemHealthResponse)
def get_operations_system_health(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    now = datetime.now(timezone.utc)
    stale_after = max(30, settings.notification_worker_poll_seconds * 3 + 15)
    heartbeat = db.scalar(
        select(WorkerHeartbeat).where(WorkerHeartbeat.worker_name == "notification-worker")
    )

    if heartbeat is None:
        worker_status = "not_seen"
        last_seen = None
        worker_age = None
    else:
        last_seen = heartbeat.last_seen_at
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        worker_age = max(0, int((now - last_seen).total_seconds()))
        worker_status = "healthy" if worker_age <= stale_after else "stale"

    rows = db.execute(
        select(NotificationDelivery.status, func.count(NotificationDelivery.id))
        .group_by(NotificationDelivery.status)
    ).all()
    queue_counts = {status: count for status, count in rows}

    return OperationsSystemHealthResponse(
        database_status="ok",
        notification_worker_status=worker_status,
        worker_last_seen_at=last_seen,
        worker_age_seconds=worker_age,
        worker_stale_after_seconds=stale_after,
        notification_queue=queue_counts,
        checked_at=now,
    )
