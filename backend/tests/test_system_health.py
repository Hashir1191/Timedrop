from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import NotificationDelivery, User, WorkerHeartbeat
from app.security import hash_password
from app import notification_worker


@pytest.fixture()
def health_client_and_sessions():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    with sessions() as db:
        db.add(User(
            email="system-health-admin@example.com",
            full_name="System Health Admin",
            password_hash=hash_password("StrongSystemHealthAdminPassword123!"),
            role="admin",
        ))
        db.add(User(
            email="system-health-customer@example.com",
            full_name="System Health Customer",
            password_hash=hash_password("StrongSystemHealthCustomerPassword123!"),
            role="customer",
        ))
        db.commit()

    def override_get_db():
        session = sessions()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, sessions
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _login(client, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _seed_delivery(sessions, status, key):
    with sessions() as db:
        item = NotificationDelivery(
            channel="email",
            recipient="ops@example.com",
            subject="System health test",
            body="Synthetic notification body",
            idempotency_key=key,
            status=status,
            attempts=1,
            next_attempt_at=datetime.now(timezone.utc),
        )
        db.add(item)
        db.commit()


def test_system_health_reports_worker_and_queue_counts(health_client_and_sessions):
    client, sessions = health_client_and_sessions
    admin = _login(client, "system-health-admin@example.com", "StrongSystemHealthAdminPassword123!")
    now = datetime.now(timezone.utc)
    with sessions() as db:
        db.add(WorkerHeartbeat(
            worker_name="notification-worker",
            last_seen_at=now,
            updated_at=now,
        ))
        db.commit()
    _seed_delivery(sessions, "pending", "system-health-pending")
    _seed_delivery(sessions, "failed", "system-health-failed")

    response = client.get("/api/v1/operations/system-health", headers=admin)

    assert response.status_code == 200
    body = response.json()
    assert body["database_status"] == "ok"
    assert body["notification_worker_status"] == "healthy"
    assert body["worker_age_seconds"] is not None
    assert body["notification_queue"]["pending"] == 1
    assert body["notification_queue"]["failed"] == 1


def test_system_health_marks_missing_worker_heartbeat(health_client_and_sessions):
    client, _ = health_client_and_sessions
    admin = _login(client, "system-health-admin@example.com", "StrongSystemHealthAdminPassword123!")

    response = client.get("/api/v1/operations/system-health", headers=admin)

    assert response.status_code == 200
    assert response.json()["notification_worker_status"] == "not_seen"
    assert response.json()["worker_last_seen_at"] is None


def test_system_health_marks_old_worker_heartbeat_stale(health_client_and_sessions):
    client, sessions = health_client_and_sessions
    admin = _login(client, "system-health-admin@example.com", "StrongSystemHealthAdminPassword123!")
    old = datetime.now(timezone.utc) - timedelta(minutes=5)
    with sessions() as db:
        db.add(WorkerHeartbeat(
            worker_name="notification-worker",
            last_seen_at=old,
            updated_at=old,
        ))
        db.commit()

    response = client.get("/api/v1/operations/system-health", headers=admin)

    assert response.status_code == 200
    assert response.json()["notification_worker_status"] == "stale"
    assert response.json()["worker_age_seconds"] >= 300


def test_system_health_is_admin_only(health_client_and_sessions):
    client, _ = health_client_and_sessions
    customer = _login(
        client,
        "system-health-customer@example.com",
        "StrongSystemHealthCustomerPassword123!",
    )

    response = client.get("/api/v1/operations/system-health", headers=customer)

    assert response.status_code == 403


def test_notification_worker_heartbeat_upserts_single_named_row(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(notification_worker, "SessionLocal", sessions)

    notification_worker._record_worker_heartbeat()
    notification_worker._record_worker_heartbeat()

    with sessions() as db:
        rows = db.scalars(select(WorkerHeartbeat)).all()
        assert len(rows) == 1
        assert rows[0].worker_name == "notification-worker"
        assert rows[0].last_seen_at is not None
        assert rows[0].updated_at is not None

    Base.metadata.drop_all(bind=engine)
    engine.dispose()
