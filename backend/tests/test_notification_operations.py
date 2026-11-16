from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import NotificationDelivery, OperationsAuditLog, User
from app.security import hash_password


@pytest.fixture()
def client_and_sessions():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    with sessions() as db:
        db.add(User(
            email="notify-admin@example.com",
            full_name="Notification Admin",
            password_hash=hash_password("StrongNotificationAdminPassword123!"),
            role="admin",
        ))
        db.commit()

    def override_get_db():
        session = sessions()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client, sessions
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _auth(client, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _delivery(sessions, *, status="failed", recipient="hashir@example.com", channel="email"):
    with sessions() as db:
        item = NotificationDelivery(
            channel=channel,
            recipient=recipient,
            subject="Delivery update",
            body="Your parcel has an update.",
            idempotency_key=f"test-notification-{datetime.now(timezone.utc).timestamp()}",
            status=status,
            attempts=3,
            next_attempt_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            last_error="Provider temporarily unavailable",
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item.id


def test_notification_delivery_list_masks_recipient_and_is_admin_only(client_and_sessions):
    client, sessions = client_and_sessions
    delivery_id = _delivery(sessions)
    admin = _auth(client, "notify-admin@example.com", "StrongNotificationAdminPassword123!")

    response = client.get("/api/v1/operations/notification-deliveries?status=failed", headers=admin)

    assert response.status_code == 200
    item = next(item for item in response.json() if item["id"] == delivery_id)
    assert item["masked_recipient"] == "h***@example.com"
    assert "hashir@example.com" not in response.text
    assert item["status"] == "failed"
    assert item["attempts"] == 3


def test_customer_cannot_access_notification_delivery_operations(client_and_sessions):
    client, sessions = client_and_sessions
    client.post("/api/v1/auth/register", json={
        "email": "notify-customer@example.com",
        "full_name": "Notification Customer",
        "password": "StrongNotificationCustomerPassword123!",
    })
    customer = _auth(client, "notify-customer@example.com", "StrongNotificationCustomerPassword123!")

    response = client.get("/api/v1/operations/notification-deliveries", headers=customer)

    assert response.status_code == 403


def test_admin_can_retry_failed_notification_and_audit_it(client_and_sessions):
    client, sessions = client_and_sessions
    delivery_id = _delivery(sessions)
    admin = _auth(client, "notify-admin@example.com", "StrongNotificationAdminPassword123!")

    response = client.post(
        f"/api/v1/operations/notification-deliveries/{delivery_id}/retry",
        headers=admin,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert response.json()["attempts"] == 3
    assert response.json()["last_error"] is None

    with sessions() as db:
        event = db.scalar(select(OperationsAuditLog).where(
            OperationsAuditLog.action == "notification_delivery.requeued"
        ))
        item = db.get(NotificationDelivery, delivery_id)
        assert event is not None
        assert item.status == "pending"


def test_admin_cannot_retry_non_failed_notification(client_and_sessions):
    client, sessions = client_and_sessions
    delivery_id = _delivery(sessions, status="sent")
    admin = _auth(client, "notify-admin@example.com", "StrongNotificationAdminPassword123!")

    response = client.post(
        f"/api/v1/operations/notification-deliveries/{delivery_id}/retry",
        headers=admin,
    )

    assert response.status_code == 409


def test_notification_delivery_filters_validate_values(client_and_sessions):
    client, _ = client_and_sessions
    admin = _auth(client, "notify-admin@example.com", "StrongNotificationAdminPassword123!")

    response = client.get(
        "/api/v1/operations/notification-deliveries?status=unknown",
        headers=admin,
    )

    assert response.status_code == 422
