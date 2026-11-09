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
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=test_engine)

    db = TestingSessionLocal()
    admin = User(
        email="ops@example.com",
        full_name="Test Operations",
        password_hash=hash_password("StrongTestPassword123!"),
        role="admin",
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.close()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        login = test_client.post(
            "/api/v1/auth/login",
            json={"email": "ops@example.com", "password": "StrongTestPassword123!"},
        )
        assert login.status_code == 200
        test_client.headers.update(
            {"Authorization": f"Bearer {login.json()['access_token']}"}
        )
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def parcel_payload(tracking_number="TD-TEST-001"):
    return {
        "tracking_number": tracking_number,
        "recipient_name": "Test Recipient",
        "phone": "9876543210",
        "address_line": "12 Test Street",
        "city": "Prayagraj",
        "state": "Uttar Pradesh",
        "pincode": "211001",
    }


def future_date():
    return (datetime.now().date() + timedelta(days=2)).isoformat()


def create_parcel(client, tracking_number="TD-TEST-001"):
    response = client.post("/api/v1/parcels/", json=parcel_payload(tracking_number))
    assert response.status_code == 201
    return response.json()["id"]


def create_slot(client, capacity=1, start="10:00:00", end="12:00:00"):
    response = client.post(
        "/api/v1/scheduling/slots",
        json={
            "delivery_date": future_date(),
            "start_time": start,
            "end_time": end,
            "capacity": capacity,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_slot_and_list_availability(client):
    slot_id = create_slot(client, capacity=3)
    response = client.get(f"/api/v1/scheduling/slots?delivery_date={future_date()}")
    assert response.status_code == 200
    assert response.json()[0]["id"] == slot_id
    assert response.json()[0]["remaining_capacity"] == 3


def test_booking_reserves_capacity_and_prevents_overbooking(client):
    first_parcel = create_parcel(client, "TD-TEST-101")
    second_parcel = create_parcel(client, "TD-TEST-102")
    slot_id = create_slot(client, capacity=1)

    first = client.post(
        f"/api/v1/scheduling/parcels/{first_parcel}/bookings",
        json={"slot_id": slot_id},
    )
    second = client.post(
        f"/api/v1/scheduling/parcels/{second_parcel}/bookings",
        json={"slot_id": slot_id},
    )

    assert first.status_code == 201
    assert second.status_code == 409
    availability = client.get(f"/api/v1/scheduling/slots?delivery_date={future_date()}").json()
    assert availability[0]["remaining_capacity"] == 0


def test_reschedule_releases_old_slot_and_reserves_new_slot(client):
    parcel_id = create_parcel(client, "TD-TEST-201")
    first_slot = create_slot(client, capacity=1, start="10:00:00", end="12:00:00")
    second_slot_response = client.post(
        "/api/v1/scheduling/slots",
        json={
            "delivery_date": future_date(),
            "start_time": "13:00:00",
            "end_time": "15:00:00",
            "capacity": 1,
        },
    )
    assert second_slot_response.status_code == 201
    second_slot = second_slot_response.json()["id"]

    assert client.post(
        f"/api/v1/scheduling/parcels/{parcel_id}/bookings",
        json={"slot_id": first_slot},
    ).status_code == 201

    moved = client.patch(
        f"/api/v1/scheduling/parcels/{parcel_id}/bookings",
        json={"slot_id": second_slot},
    )
    assert moved.status_code == 200
    assert moved.json()["slot_id"] == second_slot

    availability = client.get(f"/api/v1/scheduling/slots?delivery_date={future_date()}").json()
    by_id = {slot["id"]: slot for slot in availability}
    assert by_id[first_slot]["remaining_capacity"] == 1
    assert by_id[second_slot]["remaining_capacity"] == 0


def test_cancel_booking_releases_capacity(client):
    parcel_id = create_parcel(client, "TD-TEST-301")
    slot_id = create_slot(client, capacity=1)
    booked = client.post(
        f"/api/v1/scheduling/parcels/{parcel_id}/bookings",
        json={"slot_id": slot_id},
    )
    assert booked.status_code == 201

    cancelled = client.delete(f"/api/v1/scheduling/parcels/{parcel_id}/bookings")
    assert cancelled.status_code == 204

    availability = client.get(f"/api/v1/scheduling/slots?delivery_date={future_date()}").json()
    assert availability[0]["remaining_capacity"] == 1


def test_duplicate_slot_window_is_rejected(client):
    create_slot(client)
    duplicate = client.post(
        "/api/v1/scheduling/slots",
        json={
            "delivery_date": future_date(),
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "capacity": 4,
        },
    )
    assert duplicate.status_code == 409


def test_overlapping_slot_window_is_rejected(client):
    create_slot(client, capacity=2, start="10:00:00", end="12:00:00")
    overlapping = client.post(
        "/api/v1/scheduling/slots",
        json={
            "delivery_date": future_date(),
            "start_time": "11:30:00",
            "end_time": "13:30:00",
            "capacity": 2,
        },
    )
    assert overlapping.status_code == 409


def test_admin_booking_list_includes_parcel_and_slot_details_and_filters(client):
    parcel_id = create_parcel(client, "TD-TEST-BOOKING-LIST")
    slot_id = create_slot(client, capacity=2)
    created = client.post(
        f"/api/v1/scheduling/parcels/{parcel_id}/bookings",
        json={"slot_id": slot_id},
    )
    assert created.status_code == 201

    listed = client.get("/api/v1/scheduling/bookings?status=booked")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    item = listed.json()[0]
    assert item["parcel"]["tracking_number"] == "TD-TEST-BOOKING-LIST"
    assert item["parcel"]["recipient_name"] == "Test Recipient"
    assert item["slot"]["id"] == slot_id
    assert item["slot"]["delivery_date"] == future_date()
    assert item["status"] == "booked"

    cancelled = client.delete(f"/api/v1/scheduling/parcels/{parcel_id}/bookings")
    assert cancelled.status_code == 204
    assert client.get("/api/v1/scheduling/bookings?status=booked").json() == []
    history = client.get("/api/v1/scheduling/bookings?status=cancelled")
    assert history.status_code == 200
    assert history.json()[0]["status"] == "cancelled"


def test_customer_cannot_access_admin_booking_list(client):
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": "booking-customer@example.com",
            "full_name": "Booking Customer",
            "password": "CustomerPassword123!",
        },
    )
    assert registered.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "booking-customer@example.com", "password": "CustomerPassword123!"},
    )
    assert login.status_code == 200
    response = client.get(
        "/api/v1/scheduling/bookings",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert response.status_code == 403
