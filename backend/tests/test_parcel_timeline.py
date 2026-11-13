from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

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
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = session_factory()
    db.add_all([
        User(email="timeline-admin@example.com", full_name="Timeline Admin",
             password_hash=hash_password("StrongTestPassword123!"), role="admin"),
        User(email="timeline-owner@example.com", full_name="Parcel Owner",
             password_hash=hash_password("CustomerPassword123!"), role="customer"),
        User(email="timeline-other@example.com", full_name="Other Customer",
             password_hash=hash_password("CustomerPassword123!"), role="customer"),
    ])
    db.commit()
    db.close()

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        tokens = {}
        for email, password in [
            ("timeline-admin@example.com", "StrongTestPassword123!"),
            ("timeline-owner@example.com", "CustomerPassword123!"),
            ("timeline-other@example.com", "CustomerPassword123!"),
        ]:
            response = test_client.post("/api/v1/auth/login", json={"email": email, "password": password})
            assert response.status_code == 200
            tokens[email] = {"Authorization": f"Bearer {response.json()['access_token']}"}
        yield test_client, tokens

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_customer_timeline_includes_registration_and_booking(client):
    api, tokens = client
    owner_headers = tokens["timeline-owner@example.com"]
    admin_headers = tokens["timeline-admin@example.com"]
    parcel = api.post(
        "/api/v1/parcels/",
        headers=owner_headers,
        json={
            "tracking_number": "TD-TIMELINE-001",
            "recipient_name": "Timeline Recipient",
            "phone": "9876543210",
            "address_line": "12 Timeline Street",
            "city": "Prayagraj",
            "state": "Uttar Pradesh",
            "pincode": "211001",
        },
    )
    assert parcel.status_code == 201
    parcel_id = parcel.json()["id"]

    delivery_date = (datetime.now(ZoneInfo("Asia/Kolkata")).date() + timedelta(days=2)).isoformat()
    slot = api.post(
        "/api/v1/scheduling/slots",
        headers=admin_headers,
        json={"delivery_date": delivery_date, "start_time": "10:00:00", "end_time": "12:00:00", "capacity": 2},
    )
    assert slot.status_code == 201
    booking = api.post(
        f"/api/v1/scheduling/parcels/{parcel_id}/bookings",
        headers=owner_headers,
        json={"slot_id": slot.json()["id"]},
    )
    assert booking.status_code == 201

    timeline = api.get(f"/api/v1/parcels/{parcel_id}/timeline", headers=owner_headers)
    assert timeline.status_code == 200
    assert [event["event_type"] for event in timeline.json()] == ["parcel_registered", "booking_booked"]
    assert timeline.json()[1]["title"] == "Delivery slot booked"


def test_customer_cannot_read_another_customers_timeline(client):
    api, tokens = client
    owner_headers = tokens["timeline-owner@example.com"]
    other_headers = tokens["timeline-other@example.com"]
    parcel = api.post(
        "/api/v1/parcels/",
        headers=owner_headers,
        json={
            "tracking_number": "TD-TIMELINE-PRIVATE",
            "recipient_name": "Private Recipient",
            "phone": "9876543210",
            "address_line": "12 Private Street",
            "city": "Prayagraj",
            "state": "Uttar Pradesh",
            "pincode": "211001",
        },
    )
    assert parcel.status_code == 201
    response = api.get(
        f"/api/v1/parcels/{parcel.json()['id']}/timeline",
        headers=other_headers,
    )
    assert response.status_code == 404
