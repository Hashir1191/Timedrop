from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DeliveryAssignment, DeliveryPartner, Parcel, User
from app.security import require_admin

router = APIRouter(prefix="/api/v1/operations", tags=["Operations analytics"])


class PartnerPerformance(BaseModel):
    partner_id: int
    partner_name: str
    total_assignments: int
    delivered: int
    failed: int
    active: int
    success_rate: float
    average_delivery_hours: float | None
    on_time_delivered: int
    late_delivered: int
    on_time_rate: float


class DailyDeliveryMetric(BaseModel):
    day: date
    assigned: int
    delivered: int
    failed: int
    on_time: int
    late: int


class OperationsAnalyticsResponse(BaseModel):
    start_date: date
    end_date: date
    parcels_created: int
    assignments_created: int
    delivered: int
    failed: int
    active: int
    success_rate: float
    average_delivery_hours: float | None
    eta_covered_deliveries: int
    on_time_delivered: int
    late_delivered: int
    on_time_rate: float
    average_delay_minutes: float | None
    overdue_active: int
    partner_count: int
    partners: list[PartnerPerformance]
    daily: list[DailyDeliveryMetric]


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


@router.get("/analytics", response_model=OperationsAnalyticsResponse)
def get_operations_analytics(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Summarize recorded parcel and assignment outcomes for an inclusive date range."""
    today = datetime.now(timezone.utc).date()
    selected_end = end_date or today
    selected_start = start_date or (selected_end - timedelta(days=29))
    if selected_start > selected_end:
        raise HTTPException(status_code=422, detail="start_date must be on or before end_date.")
    if (selected_end - selected_start).days > 365:
        raise HTTPException(status_code=422, detail="Date range cannot exceed 366 calendar days.")

    start_at = datetime.combine(selected_start, time.min, tzinfo=timezone.utc)
    end_at = datetime.combine(selected_end + timedelta(days=1), time.min, tzinfo=timezone.utc)
    parcels_created = db.query(Parcel).filter(
        Parcel.created_at >= start_at, Parcel.created_at < end_at
    ).count()

    rows = db.execute(
        select(DeliveryAssignment, DeliveryPartner, User)
        .join(DeliveryPartner, DeliveryPartner.id == DeliveryAssignment.partner_id)
        .join(User, User.id == DeliveryPartner.user_id)
        .where(DeliveryAssignment.assigned_at >= start_at, DeliveryAssignment.assigned_at < end_at)
        .order_by(User.full_name, DeliveryAssignment.id)
    ).all()

    delivered = sum(1 for assignment, _, _ in rows if assignment.status == "delivered")
    failed = sum(1 for assignment, _, _ in rows if assignment.status == "failed")
    active = sum(
        1 for assignment, _, _ in rows
        if assignment.status in {"assigned", "accepted", "out_for_delivery"}
    )
    completed = delivered + failed
    success_rate = round((delivered / completed) * 100, 1) if completed else 0.0
    durations = [
        (_utc(assignment.delivered_at) - _utc(assignment.assigned_at)).total_seconds() / 3600
        for assignment, _, _ in rows
        if assignment.status == "delivered" and assignment.delivered_at is not None
        and _utc(assignment.delivered_at) >= _utc(assignment.assigned_at)
    ]
    average_hours = round(sum(durations) / len(durations), 2) if durations else None

    now = datetime.now(timezone.utc)
    eta_deliveries = [
        assignment for assignment, _, _ in rows
        if assignment.status == "delivered"
        and assignment.delivered_at is not None
        and assignment.estimated_delivery_start is not None
        and assignment.estimated_delivery_end is not None
    ]
    on_time_delivered = sum(
        1 for assignment in eta_deliveries
        if _utc(assignment.delivered_at) <= _utc(assignment.estimated_delivery_end)
    )
    late_deliveries = [
        assignment for assignment in eta_deliveries
        if _utc(assignment.delivered_at) > _utc(assignment.estimated_delivery_end)
    ]
    late_delivered = len(late_deliveries)
    on_time_rate = round(on_time_delivered / len(eta_deliveries) * 100, 1) if eta_deliveries else 0.0
    delay_minutes = [
        (_utc(assignment.delivered_at) - _utc(assignment.estimated_delivery_end)).total_seconds() / 60
        for assignment in late_deliveries
    ]
    average_delay_minutes = round(sum(delay_minutes) / len(delay_minutes), 1) if delay_minutes else None
    overdue_active = sum(
        1 for assignment, _, _ in rows
        if assignment.status in {"assigned", "accepted", "out_for_delivery"}
        and assignment.estimated_delivery_end is not None
        and _utc(assignment.estimated_delivery_end) < now
    )

    partner_groups: dict[int, dict] = {}
    for assignment, partner, user in rows:
        item = partner_groups.setdefault(partner.id, {
            "partner_id": partner.id, "partner_name": user.full_name,
            "total_assignments": 0, "delivered": 0, "failed": 0, "active": 0,
            "durations": [],
            "eta_covered": 0,
            "on_time_delivered": 0,
            "late_delivered": 0,
        })
        item["total_assignments"] += 1
        if assignment.status == "delivered":
            item["delivered"] += 1
            if assignment.delivered_at is not None:
                elapsed = (_utc(assignment.delivered_at) - _utc(assignment.assigned_at)).total_seconds() / 3600
                if elapsed >= 0:
                    item["durations"].append(elapsed)
            if assignment.delivered_at is not None and assignment.estimated_delivery_start is not None and assignment.estimated_delivery_end is not None:
                item["eta_covered"] += 1
                if _utc(assignment.delivered_at) <= _utc(assignment.estimated_delivery_end):
                    item["on_time_delivered"] += 1
                else:
                    item["late_delivered"] += 1
        elif assignment.status == "failed":
            item["failed"] += 1
        elif assignment.status in {"assigned", "accepted", "out_for_delivery"}:
            item["active"] += 1

    partners = []
    for item in partner_groups.values():
        terminal = item["delivered"] + item["failed"]
        partner_durations = item.pop("durations")
        partners.append(PartnerPerformance(
            **item,
            success_rate=round(item["delivered"] / terminal * 100, 1) if terminal else 0.0,
            average_delivery_hours=round(sum(partner_durations) / len(partner_durations), 2)
            if partner_durations else None,
            on_time_delivered=item["on_time_delivered"],
            late_delivered=item["late_delivered"],
            on_time_rate=round(item["on_time_delivered"] / item["eta_covered"] * 100, 1)
            if item["eta_covered"] else 0.0,
        ))
    partners.sort(key=lambda item: (-item.delivered, -item.total_assignments, item.partner_name.lower()))

    daily_map = {
        selected_start + timedelta(days=offset): {"assigned": 0, "delivered": 0, "failed": 0, "on_time": 0, "late": 0}
        for offset in range((selected_end - selected_start).days + 1)
    }
    for assignment, _, _ in rows:
        assigned_day = _utc(assignment.assigned_at).date()
        if assigned_day in daily_map:
            daily_map[assigned_day]["assigned"] += 1
        if assignment.status == "delivered" and assignment.delivered_at is not None:
            outcome_day = _utc(assignment.delivered_at).date()
            if outcome_day in daily_map:
                daily_map[outcome_day]["delivered"] += 1
                if assignment.estimated_delivery_start is not None and assignment.estimated_delivery_end is not None:
                    if _utc(assignment.delivered_at) <= _utc(assignment.estimated_delivery_end):
                        daily_map[outcome_day]["on_time"] += 1
                    else:
                        daily_map[outcome_day]["late"] += 1
        elif assignment.status == "failed":
            outcome_day = _utc(assignment.updated_at).date()
            if outcome_day in daily_map:
                daily_map[outcome_day]["failed"] += 1

    return OperationsAnalyticsResponse(
        start_date=selected_start,
        end_date=selected_end,
        parcels_created=parcels_created,
        assignments_created=len(rows),
        delivered=delivered,
        failed=failed,
        active=active,
        success_rate=success_rate,
        average_delivery_hours=average_hours,
        eta_covered_deliveries=len(eta_deliveries),
        on_time_delivered=on_time_delivered,
        late_delivered=late_delivered,
        on_time_rate=on_time_rate,
        average_delay_minutes=average_delay_minutes,
        overdue_active=overdue_active,
        partner_count=len(partner_groups),
        partners=partners,
        daily=[
            DailyDeliveryMetric(day=day, **values)
            for day, values in daily_map.items()
        ],
    )
