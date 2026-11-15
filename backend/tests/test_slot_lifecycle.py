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
        User(email="slot-admin@example.com", full_name="Slot Admin",
             password_hash=hash_password("StrongSlotAdminPassword123!"), role="admin"),
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


def delivery_date():
    return (date.today() + timedelta(days=6)).isoformat()


def make_slot(client, admin, capacity=5):
    return client.post("/api/v1/scheduling/slots", headers=admin, json={
        "delivery_date": delivery_date(),
        "start_time": "10:00:00",
        "end_time": "12:00:00",
        "capacity": capacity,
    })


def register_customer(client, email):
    client.post("/api/v1/auth/register", json={
        "email": email,
        "full_name": "Slot Customer",
        "password": "StrongSlotCustomerPassword123!",
    })
    return auth(client, email, "StrongSlotCustomerPassword123!")


def create_parcel(client, customer, tracking):
    response = client.post("/api/v1/parcels/", headers=customer, json={
        "tracking_number": tracking,
        "recipient_name": "Synthetic Recipient",
        "phone": "9876543210",
        "address_line": "12 Example Test Street",
        "city": "Prayagraj",
        "state": "Uttar Pradesh",
        "pincode": "211001",
    })
    assert response.status_code == 201
    return response.json()


def test_admin_can_edit_capacity_pause_and_reactivate_slot(client):
    admin = auth(client, "slot-admin@example.com", "StrongSlotAdminPassword123!")
    slot = make_slot(client, admin)
    assert slot.status_code == 201
    slot_id = slot.json()["id"]

    updated = client.patch(
        f"/api/v1/scheduling/slots/{slot_id}",
        headers=admin,
        json={"capacity": 8},
    )
    assert updated.status_code == 200
    assert updated.json()["capacity"] == 8

    paused = client.patch(
        f"/api/v1/scheduling/slots/{slot_id}",
        headers=admin,
        json={"is_active": False},
    )
    assert paused.status_code == 200
    assert paused.json()["is_active"] is False

    admin_slots = client.get(
        f"/api/v1/scheduling/slots?delivery_date={delivery_date()}&include_inactive=true",
        headers=admin,
    )
    assert admin_slots.status_code == 200
    assert admin_slots.json()[0]["is_active"] is False

    customer = register_customer(client, "slot-viewer@example.com")
    assert client.get(
        f"/api/v1/scheduling/slots?delivery_date={delivery_date()}&include_inactive=true",
        headers=customer,
    ).status_code == 403
    assert client.get(
        f"/api/v1/scheduling/slots?delivery_date={delivery_date()}",
        headers=customer,
    ).json() == []

    reactivated = client.patch(
        f"/api/v1/scheduling/slots/{slot_id}",
        headers=admin,
        json={"is_active": True},
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True


def test_slot_capacity_and_deactivation_respect_confirmed_bookings(client):
    admin = auth(client, "slot-admin@example.com", "StrongSlotAdminPassword123!")
    slot = make_slot(client, admin, capacity=2)
    assert slot.status_code == 201
    customer = register_customer(client, "slot-booking-customer@example.com")

    for tracking in ("TD-SLOT-CAPACITY-1", "TD-SLOT-CAPACITY-2"):
        parcel = create_parcel(client, customer, tracking)
        booking = client.post(
            f"/api/v1/scheduling/parcels/{parcel['id']}/bookings",
            headers=customer,
            json={"slot_id": slot.json()["id"]},
        )
        assert booking.status_code == 201

    capacity_reduction = client.patch(
        f"/api/v1/scheduling/slots/{slot.json()['id']}",
        headers=admin,
        json={"capacity": 1},
    )
    assert capacity_reduction.status_code == 409
    assert "confirmed booking" in capacity_reduction.json()["detail"]

    pause = client.patch(
        f"/api/v1/scheduling/slots/{slot.json()['id']}",
        headers=admin,
        json={"is_active": False},
    )
    assert pause.status_code == 409
    assert "confirmed bookings" in pause.json()["detail"]


def test_slot_reactivation_is_blocked_by_blackout_date(client):
    admin = auth(client, "slot-admin@example.com", "StrongSlotAdminPassword123!")
    slot = make_slot(client, admin)
    assert slot.status_code == 201
    paused = client.patch(
        f"/api/v1/scheduling/slots/{slot.json()['id']}",
        headers=admin,
        json={"is_active": False},
    )
    assert paused.status_code == 200

    closure = client.post("/api/v1/operations/blackout-dates", headers=admin, json={
        "delivery_date": delivery_date(),
        "reason": "Planned maintenance",
    })
    assert closure.status_code == 201
    rejected = client.patch(
        f"/api/v1/scheduling/slots/{slot.json()['id']}",
        headers=admin,
        json={"is_active": True},
    )
    assert rejected.status_code == 409
    assert "Delivery is closed" in rejected.json()["detail"]


def test_only_admin_can_update_delivery_slots(client):
    admin = auth(client, "slot-admin@example.com", "StrongSlotAdminPassword123!")
    slot = make_slot(client, admin)
    assert slot.status_code == 201
    customer = register_customer(client, "slot-permission-customer@example.com")
    rejected = client.patch(
        f"/api/v1/scheduling/slots/{slot.json()['id']}",
        headers=customer,
        json={"capacity": 10},
    )
    assert rejected.status_code == 403
