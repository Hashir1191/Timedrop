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


def test_release_records_handover_to_assigned_partner(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    client.post("/api/v1/auth/register", json={
        "email": "release-owner@example.com", "full_name": "Release Owner", "password": "CustomerPassword123!",
    })
    customer = auth(client, "release-owner@example.com", "CustomerPassword123!")
    received = client.post(
        "/api/v1/operations/intake",
        headers=admin,
        json={**intake_payload("TD-CUSTODY-RELEASE"), "customer_email": "release-owner@example.com"},
    )
    assert received.status_code == 201
    parcel_id = received.json()["id"]

    slot_response = client.post("/api/v1/scheduling/slots", headers=admin, json={
        "delivery_date": (datetime.now().date() + timedelta(days=3)).isoformat(),
        "start_time": "10:00:00", "end_time": "12:00:00", "capacity": 5,
    })
    assert slot_response.status_code == 201
    booking = client.post(
        f"/api/v1/scheduling/parcels/{parcel_id}/bookings",
        headers=customer,
        json={"slot_id": slot_response.json()["id"]},
    )
    assert booking.status_code == 201

    partner = client.post("/api/v1/delivery/partners", headers=admin, json={
        "email": "release-rider@example.com", "full_name": "Release Rider",
        "password": "StrongRiderPassword123!", "phone": "9876543211",
    })
    assert partner.status_code == 201
    assigned = client.post(
        f"/api/v1/delivery/parcels/{parcel_id}/assignments",
        headers=admin,
        json={"partner_id": partner.json()["id"]},
    )
    assert assigned.status_code == 201

    released = client.post(
        f"/api/v1/operations/parcels/{parcel_id}/release",
        headers=admin,
        json={"note": "Seal and parcel handed to rider."},
    )
    assert released.status_code == 201
    assert released.json()["event_type"] == "released"
    assert released.json()["handed_to"] == "Release Rider"

    history = client.get(f"/api/v1/operations/parcels/{parcel_id}/custody", headers=admin)
    assert [event["event_type"] for event in history.json()] == ["received", "released"]
    again = client.post(f"/api/v1/operations/parcels/{parcel_id}/release", headers=admin, json={})
    assert again.status_code == 409


def test_failed_delivery_must_return_to_operations_before_reassignment(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    client.post("/api/v1/auth/register", json={
        "email": "return-owner@example.com", "full_name": "Return Owner", "password": "CustomerPassword123!",
    })
    customer = auth(client, "return-owner@example.com", "CustomerPassword123!")
    received = client.post(
        "/api/v1/operations/intake",
        headers=admin,
        json={**intake_payload("TD-CUSTODY-RETURN"), "customer_email": "return-owner@example.com"},
    )
    assert received.status_code == 201
    parcel_id = received.json()["id"]

    slot_response = client.post("/api/v1/scheduling/slots", headers=admin, json={
        "delivery_date": (datetime.now().date() + timedelta(days=3)).isoformat(),
        "start_time": "10:00:00", "end_time": "12:00:00", "capacity": 5,
    })
    assert slot_response.status_code == 201
    booking = client.post(
        f"/api/v1/scheduling/parcels/{parcel_id}/bookings",
        headers=customer,
        json={"slot_id": slot_response.json()["id"]},
    )
    assert booking.status_code == 201

    partner = client.post("/api/v1/delivery/partners", headers=admin, json={
        "email": "return-rider@example.com", "full_name": "Return Rider",
        "password": "StrongRiderPassword123!", "phone": "9876543212",
    })
    assert partner.status_code == 201
    assignment = client.post(
        f"/api/v1/delivery/parcels/{parcel_id}/assignments",
        headers=admin,
        json={"partner_id": partner.json()["id"]},
    )
    assert assignment.status_code == 201
    released = client.post(
        f"/api/v1/operations/parcels/{parcel_id}/release",
        headers=admin,
        json={},
    )
    assert released.status_code == 201

    rider = auth(client, "return-rider@example.com", "StrongRiderPassword123!")
    assert client.patch(
        f"/api/v1/delivery/assignments/{assignment.json()['id']}/status",
        headers=rider,
        json={"status": "accepted"},
    ).status_code == 200
    assert client.patch(
        f"/api/v1/delivery/assignments/{assignment.json()['id']}/status",
        headers=rider,
        json={"status": "out_for_delivery"},
    ).status_code == 200
    failed = client.patch(
        f"/api/v1/delivery/assignments/{assignment.json()['id']}/status",
        headers=rider,
        json={"status": "failed", "failure_reason": "Recipient unavailable"},
    )
    assert failed.status_code == 200

    blocked = client.post(
        f"/api/v1/delivery/parcels/{parcel_id}/assignments",
        headers=admin,
        json={"partner_id": partner.json()["id"]},
    )
    assert blocked.status_code == 409

    returned = client.post(
        f"/api/v1/operations/parcels/{parcel_id}/return",
        headers=admin,
        json={"package_condition": "damaged", "note": "Outer packaging torn; received back at depot."},
    )
    assert returned.status_code == 201
    assert returned.json()["event_type"] == "returned"
    assert returned.json()["received_from"] == "Return Rider"
    assert returned.json()["package_condition"] == "damaged"

    reassigned = client.post(
        f"/api/v1/delivery/parcels/{parcel_id}/assignments",
        headers=admin,
        json={"partner_id": partner.json()["id"]},
    )
    assert reassigned.status_code == 201
    released_again = client.post(
        f"/api/v1/operations/parcels/{parcel_id}/release",
        headers=admin,
        json={"note": "Reissued after return inspection."},
    )
    assert released_again.status_code == 201

    history = client.get(f"/api/v1/operations/parcels/{parcel_id}/custody", headers=admin)
    assert [event["event_type"] for event in history.json()] == [
        "received", "released", "returned", "released",
    ]


def test_only_operations_admin_can_record_failed_parcel_return(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    client.post("/api/v1/auth/register", json={
        "email": "ordinary-customer@example.com", "full_name": "Customer", "password": "CustomerPassword123!",
    })
    customer = auth(client, "ordinary-customer@example.com", "CustomerPassword123!")
    response = client.post(
        "/api/v1/operations/parcels/999/return",
        headers=customer,
        json={"package_condition": "intact", "note": "Synthetic return"},
    )
    assert response.status_code == 403


def test_warehouse_summary_and_inventory_search_are_admin_only(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    created = client.post(
        "/api/v1/operations/intake",
        headers=admin,
        json=intake_payload("TD-WAREHOUSE-001"),
    )
    assert created.status_code == 201

    summary = client.get("/api/v1/operations/warehouse/summary", headers=admin)
    assert summary.status_code == 200
    assert summary.json()["total_parcels"] == 1
    assert summary.json()["in_custody"] == 1
    assert summary.json()["awaiting_storage"] == 1

    rows = client.get(
        "/api/v1/operations/warehouse/parcels?q=TD-WAREHOUSE&parcel_status=registered",
        headers=admin,
    )
    assert rows.status_code == 200
    assert len(rows.json()) == 1
    assert rows.json()[0]["tracking_number"] == "TD-WAREHOUSE-001"

    client.post("/api/v1/auth/register", json={
        "email": "warehouse-customer@example.com",
        "full_name": "Warehouse Customer",
        "password": "CustomerPassword123!",
    })
    customer = auth(client, "warehouse-customer@example.com", "CustomerPassword123!")
    assert client.get("/api/v1/operations/warehouse/summary", headers=customer).status_code == 403
    assert client.get("/api/v1/operations/warehouse/parcels", headers=customer).status_code == 403


def test_storage_bin_can_only_be_assigned_while_parcel_is_in_operations_custody(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    received = client.post(
        "/api/v1/operations/intake",
        headers=admin,
        json=intake_payload("TD-WAREHOUSE-BIN-001"),
    )
    assert received.status_code == 201
    parcel_id = received.json()["id"]

    assigned = client.patch(
        f"/api/v1/operations/warehouse/parcels/{parcel_id}/location",
        headers=admin,
        json={"warehouse_location": "A-01-02"},
    )
    assert assigned.status_code == 200
    assert assigned.json()["warehouse_location"] == "A-01-02"

    summary = client.get("/api/v1/operations/warehouse/summary", headers=admin)
    assert summary.json()["assigned_to_bins"] == 1
    assert summary.json()["awaiting_storage"] == 0

    cleared = client.patch(
        f"/api/v1/operations/warehouse/parcels/{parcel_id}/location",
        headers=admin,
        json={"warehouse_location": "  "},
    )
    assert cleared.status_code == 200
    assert cleared.json()["warehouse_location"] is None


def test_storage_bin_cannot_be_updated_after_parcel_is_released(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    received = client.post(
        "/api/v1/operations/intake",
        headers=admin,
        json=intake_payload("TD-WAREHOUSE-BIN-002"),
    )
    parcel_id = received.json()["id"]

    client.post("/api/v1/auth/register", json={
        "email": "bin-owner@example.com",
        "full_name": "Bin Owner",
        "password": "CustomerPassword123!",
    })
    customer = auth(client, "bin-owner@example.com", "CustomerPassword123!")
    slot = client.post("/api/v1/scheduling/slots", headers=admin, json={
        "delivery_date": (datetime.now().date() + timedelta(days=3)).isoformat(),
        "start_time": "10:00:00", "end_time": "12:00:00", "capacity": 5,
    })
    client.post(
        f"/api/v1/scheduling/parcels/{parcel_id}/bookings",
        headers=customer,
        json={"slot_id": slot.json()["id"]},
    )
    partner = client.post("/api/v1/delivery/partners", headers=admin, json={
        "email": "bin-rider@example.com", "full_name": "Bin Rider",
        "password": "StrongRiderPassword123!", "phone": "9876543213",
    })
    client.post(
        f"/api/v1/delivery/parcels/{parcel_id}/assignments",
        headers=admin,
        json={"partner_id": partner.json()["id"]},
    )
    released = client.post(
        f"/api/v1/operations/parcels/{parcel_id}/release",
        headers=admin,
        json={},
    )
    assert released.status_code == 201

    response = client.patch(
        f"/api/v1/operations/warehouse/parcels/{parcel_id}/location",
        headers=admin,
        json={"warehouse_location": "A-01-03"},
    )
    assert response.status_code == 409
