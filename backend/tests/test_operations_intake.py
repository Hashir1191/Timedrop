from datetime import datetime, timedelta

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
    db.add(User(email="ops@example.com", full_name="Ops", password_hash=hash_password("StrongAdminPassword123!"), role="admin"))
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


def intake_payload(tracking="TD-CUSTODY-001"):
    return {
        "tracking_number": tracking,
        "recipient_name": "Synthetic Recipient",
        "phone": "9876543210",
        "address_line": "12 Example Test Street",
        "city": "Prayagraj",
        "state": "Uttar Pradesh",
        "pincode": "211001",
        "received_from": "Authorized carrier",
        "package_condition": "intact",
        "note": "Seal checked at intake",
    }


def test_admin_can_receive_parcel_and_review_append_only_custody_history(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    response = client.post("/api/v1/operations/intake", headers=admin, json=intake_payload())
    assert response.status_code == 201
    parcel = response.json()
    assert parcel["tracking_number"] == "TD-CUSTODY-001"
    assert parcel["package_condition"] == "intact"
    assert parcel["received_from"] == "Authorized carrier"

    history = client.get(f"/api/v1/operations/parcels/{parcel['id']}/custody", headers=admin)
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["event_type"] == "received"
    assert history.json()[0]["note"] == "Seal checked at intake"

    listed = client.get("/api/v1/operations/intake", headers=admin)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [parcel["id"]]


def test_intake_can_link_only_an_existing_customer_account(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    registration = client.post("/api/v1/auth/register", json={
        "email": "customer@example.com", "full_name": "Customer", "password": "CustomerPassword123!",
    })
    assert registration.status_code == 201
    response = client.post(
        "/api/v1/operations/intake",
        headers=admin,
        json={**intake_payload("TD-CUSTODY-002"), "customer_email": "customer@example.com"},
    )
    assert response.status_code == 201
    assert response.json()["customer_email"] == "customer@example.com"
    missing = client.post(
        "/api/v1/operations/intake",
        headers=admin,
        json={**intake_payload("TD-CUSTODY-003"), "customer_email": "missing@example.com"},
    )
    assert missing.status_code == 404


def test_customer_cannot_use_operations_intake_or_view_custody(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    created = client.post("/api/v1/operations/intake", headers=admin, json=intake_payload())
    assert created.status_code == 201
    client.post("/api/v1/auth/register", json={
        "email": "customer@example.com", "full_name": "Customer", "password": "CustomerPassword123!",
    })
    customer = auth(client, "customer@example.com", "CustomerPassword123!")
    assert client.post("/api/v1/operations/intake", headers=customer, json=intake_payload("TD-CUSTODY-004")).status_code == 403
    assert client.get(f"/api/v1/operations/parcels/{created.json()['id']}/custody", headers=customer).status_code == 403


def test_duplicate_tracking_number_is_rejected_without_duplicate_custody_event(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    first = client.post("/api/v1/operations/intake", headers=admin, json=intake_payload())
    duplicate = client.post("/api/v1/operations/intake", headers=admin, json=intake_payload())
    assert first.status_code == 201
    assert duplicate.status_code == 409
    history = client.get(f"/api/v1/operations/parcels/{first.json()['id']}/custody", headers=admin)
    assert len(history.json()) == 1


def test_release_requires_an_assigned_delivery_partner(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    received = client.post("/api/v1/operations/intake", headers=admin, json=intake_payload())
    assert received.status_code == 201
    parcel_id = received.json()["id"]
    response = client.post(f"/api/v1/operations/parcels/{parcel_id}/release", headers=admin, json={})
    assert response.status_code == 409
    history = client.get(f"/api/v1/operations/parcels/{parcel_id}/custody", headers=admin)
    assert [event["event_type"] for event in history.json()] == ["received"]
