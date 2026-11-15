from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import ServiceablePincode, User
from app.security import hash_password


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = sessions()
    db.add_all([
        User(email="blackout-admin@example.com", full_name="Blackout Admin",
             password_hash=hash_password("StrongBlackoutAdminPassword123!"), role="admin"),
        ServiceablePincode(pincode="211001", city="Prayagraj", state="Uttar Pradesh"),
    ])
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


def future_date():
    return (date.today() + timedelta(days=5)).isoformat()


def create_slot(client, admin, delivery_date):
    return client.post("/api/v1/scheduling/slots", headers=admin, json={
        "delivery_date": delivery_date,
        "start_time": "10:00:00",
        "end_time": "12:00:00",
        "capacity": 5,
    })


def test_blackout_prevents_slot_creation_and_customer_availability(client):
    admin = auth(client, "blackout-admin@example.com", "StrongBlackoutAdminPassword123!")
    delivery_date = future_date()
    created = client.post("/api/v1/operations/blackout-dates", headers=admin, json={
        "delivery_date": delivery_date,
        "reason": "Public holiday",
    })
    assert created.status_code == 201
    assert created.json()["is_active"] is True

    rejected_slot = create_slot(client, admin, delivery_date)
    assert rejected_slot.status_code == 409
    assert "Delivery is closed" in rejected_slot.json()["detail"]

    client.post("/api/v1/auth/register", json={
        "email": "blackout-customer@example.com",
        "full_name": "Blackout Customer",
        "password": "StrongBlackoutCustomerPassword123!",
    })
    customer = auth(client, "blackout-customer@example.com", "StrongBlackoutCustomerPassword123!")
    closure_status = client.get(
        f"/api/v1/scheduling/blackout-status?delivery_date={delivery_date}",
        headers=customer,
    )
    assert closure_status.status_code == 200
    assert closure_status.json()["is_blackout"] is True
    assert closure_status.json()["reason"] == "Public holiday"
    availability = client.get(
        f"/api/v1/scheduling/slots?delivery_date={delivery_date}",
        headers=customer,
    )
    assert availability.status_code == 200
    assert availability.json() == []


def test_blackout_cannot_be_activated_while_confirmed_bookings_exist(client):
    admin = auth(client, "blackout-admin@example.com", "StrongBlackoutAdminPassword123!")
    delivery_date = future_date()
    slot = create_slot(client, admin, delivery_date)
    assert slot.status_code == 201

    client.post("/api/v1/auth/register", json={
        "email": "booked-customer@example.com",
        "full_name": "Booked Customer",
        "password": "StrongBookedCustomerPassword123!",
    })
    customer = auth(client, "booked-customer@example.com", "StrongBookedCustomerPassword123!")
    parcel = client.post("/api/v1/parcels/", headers=customer, json={
        "tracking_number": "TD-BLACKOUT-BOOKED",
        "recipient_name": "Synthetic Recipient",
        "phone": "9876543210",
        "address_line": "12 Example Test Street",
        "city": "Prayagraj",
        "state": "Uttar Pradesh",
        "pincode": "211001",
    })
    assert parcel.status_code == 201
    booking = client.post(
        f"/api/v1/scheduling/parcels/{parcel.json()['id']}/bookings",
        headers=customer,
        json={"slot_id": slot.json()["id"]},
    )
    assert booking.status_code == 201

    rejected = client.post("/api/v1/operations/blackout-dates", headers=admin, json={
        "delivery_date": delivery_date,
        "reason": "Unexpected closure",
    })
    assert rejected.status_code == 409
    assert "active bookings" in rejected.json()["detail"]


def test_reopening_blackout_restores_existing_slots(client):
    admin = auth(client, "blackout-admin@example.com", "StrongBlackoutAdminPassword123!")
    delivery_date = future_date()
    slot = create_slot(client, admin, delivery_date)
    assert slot.status_code == 201
    blackout = client.post("/api/v1/operations/blackout-dates", headers=admin, json={
        "delivery_date": delivery_date,
        "reason": "Planned maintenance",
    })
    assert blackout.status_code == 201

    client.post("/api/v1/auth/register", json={
        "email": "reopen-customer@example.com",
        "full_name": "Reopen Customer",
        "password": "StrongReopenCustomerPassword123!",
    })
    customer = auth(client, "reopen-customer@example.com", "StrongReopenCustomerPassword123!")
    parcel = client.post("/api/v1/parcels/", headers=customer, json={
        "tracking_number": "TD-BLACKOUT-REOPEN",
        "recipient_name": "Synthetic Recipient",
        "phone": "9876543210",
        "address_line": "12 Example Test Street",
        "city": "Prayagraj",
        "state": "Uttar Pradesh",
        "pincode": "211001",
    })
    assert parcel.status_code == 201
    assert client.get(
        f"/api/v1/scheduling/slots?delivery_date={delivery_date}",
        headers=customer,
    ).json() == []
    blocked_booking = client.post(
        f"/api/v1/scheduling/parcels/{parcel.json()['id']}/bookings",
        headers=customer,
        json={"slot_id": slot.json()["id"]},
    )
    assert blocked_booking.status_code == 409

    reopened = client.patch(
        f"/api/v1/operations/blackout-dates/{blackout.json()['id']}",
        headers=admin,
        json={"is_active": False},
    )
    assert reopened.status_code == 200
    assert reopened.json()["is_active"] is False
    reopened_status = client.get(
        f"/api/v1/scheduling/blackout-status?delivery_date={delivery_date}",
        headers=customer,
    )
    assert reopened_status.status_code == 200
    assert reopened_status.json()["is_blackout"] is False
    restored = client.get(
        f"/api/v1/scheduling/slots?delivery_date={delivery_date}",
        headers=customer,
    )
    assert restored.status_code == 200
    assert [item["id"] for item in restored.json()] == [slot.json()["id"]]
    booking = client.post(
        f"/api/v1/scheduling/parcels/{parcel.json()['id']}/bookings",
        headers=customer,
        json={"slot_id": slot.json()["id"]},
    )
    assert booking.status_code == 201


def test_only_admin_can_manage_blackout_dates(client):
    admin = auth(client, "blackout-admin@example.com", "StrongBlackoutAdminPassword123!")
    client.post("/api/v1/auth/register", json={
        "email": "blackout-role-customer@example.com",
        "full_name": "Customer",
        "password": "StrongRoleCustomerPassword123!",
    })
    customer = auth(client, "blackout-role-customer@example.com", "StrongRoleCustomerPassword123!")
    payload = {"delivery_date": future_date(), "reason": "Operations closure"}
    assert client.get("/api/v1/operations/blackout-dates", headers=customer).status_code == 403
    assert client.post("/api/v1/operations/blackout-dates", headers=customer, json=payload).status_code == 403

    created = client.post("/api/v1/operations/blackout-dates", headers=admin, json=payload)
    assert created.status_code == 201
    assert client.patch(
        f"/api/v1/operations/blackout-dates/{created.json()['id']}",
        headers=customer,
        json={"is_active": False},
    ).status_code == 403
