from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.security import hash_password


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = sessions()
    db.add(User(
        email="audit-admin@example.com",
        full_name="Audit Admin",
        password_hash=hash_password("StrongAuditAdminPassword123!"),
        role="admin",
    ))
    db.commit()
    db.close()

    def override_get_db():
        session = sessions()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def auth(client, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_operations_audit_log_captures_admin_changes_and_changed_fields_only(client):
    admin = auth(client, "audit-admin@example.com", "StrongAuditAdminPassword123!")

    area = client.post("/api/v1/operations/service-areas/", headers=admin, json={
        "pincode": "211001", "city": "Prayagraj", "state": "Uttar Pradesh",
    })
    assert area.status_code == 201
    changed_area = client.patch(
        f"/api/v1/operations/service-areas/{area.json()['id']}",
        headers=admin,
        json={"is_active": False},
    )
    assert changed_area.status_code == 200

    partner = client.post("/api/v1/delivery/partners", headers=admin, json={
        "email": "audit-partner@example.com",
        "full_name": "Audit Partner",
        "password": "StrongAuditPartnerPassword123!",
        "phone": "9876543210",
        "vehicle_type": "bike",
        "max_active_assignments": 5,
    })
    assert partner.status_code == 201

    slot_date = (date.today() + timedelta(days=5)).isoformat()
    slot = client.post("/api/v1/scheduling/slots", headers=admin, json={
        "delivery_date": slot_date,
        "start_time": "10:00:00",
        "end_time": "12:00:00",
        "capacity": 5,
    })
    assert slot.status_code == 201
    changed_slot = client.patch(
        f"/api/v1/scheduling/slots/{slot.json()['id']}",
        headers=admin,
        json={"capacity": 8},
    )
    assert changed_slot.status_code == 200

    response = client.get("/api/v1/operations/audit-log?limit=100", headers=admin)
    assert response.status_code == 200
    events = response.json()
    actions = {event["action"] for event in events}
    assert {
        "service_area.created",
        "service_area.updated",
        "delivery_partner.created",
        "delivery_slot.created",
        "delivery_slot.updated",
    }.issubset(actions)

    partner_event = next(event for event in events if event["action"] == "delivery_partner.created")
    assert partner_event["actor_name"] == "Audit Admin"
    assert "phone" in partner_event["changed_fields"]
    assert "9876543210" not in response.text
    assert "audit-partner@example.com" not in response.text

    slot_events = client.get(
        "/api/v1/operations/audit-log?entity_type=delivery_slot",
        headers=admin,
    )
    assert slot_events.status_code == 200
    assert all(event["entity_type"] == "delivery_slot" for event in slot_events.json())


def test_operations_audit_log_is_admin_only_and_validates_filters(client):
    client.post("/api/v1/auth/register", json={
        "email": "audit-customer@example.com",
        "full_name": "Audit Customer",
        "password": "StrongAuditCustomerPassword123!",
    })
    customer = auth(client, "audit-customer@example.com", "StrongAuditCustomerPassword123!")
    assert client.get("/api/v1/operations/audit-log", headers=customer).status_code == 403

    admin = auth(client, "audit-admin@example.com", "StrongAuditAdminPassword123!")
    invalid_range = client.get(
        "/api/v1/operations/audit-log?from_date=2026-12-10&to_date=2026-12-01",
        headers=admin,
    )
    assert invalid_range.status_code == 422
