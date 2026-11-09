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


def make_parcel(client, headers, tracking="TD-PARTNER-001"):
    response = client.post("/api/v1/parcels/", headers=headers, json={
        "tracking_number": tracking, "recipient_name": "Synthetic Recipient",
        "phone": "9876543210", "address_line": "12 Example Test Street",
        "city": "Prayagraj", "state": "Uttar Pradesh", "pincode": "211001",
    })
    assert response.status_code == 201
    return response.json()["id"]


def book_parcel(client, headers, parcel_id):
    delivery_date = (datetime.now().date() + timedelta(days=3)).isoformat()
    slot = client.post("/api/v1/scheduling/slots", headers=auth(client, "ops@example.com", "StrongAdminPassword123!"), json={
        "delivery_date": delivery_date, "start_time": "10:00:00", "end_time": "12:00:00", "capacity": 5,
    })
    assert slot.status_code == 201
    booked = client.post(f"/api/v1/scheduling/parcels/{parcel_id}/bookings", headers=headers, json={"slot_id": slot.json()["id"]})
    assert booked.status_code == 201


def test_admin_creates_partner_and_partner_can_login(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    created = client.post("/api/v1/delivery/partners", headers=admin, json={
        "email": "rider@example.com", "full_name": "Demo Rider", "password": "StrongRiderPassword123!",
        "phone": "9876543210", "vehicle_type": "two_wheeler",
    })
    assert created.status_code == 201
    assert created.json()["email"] == "rider@example.com"
    assert created.json()["active_assignments"] == 0
    assert "password" not in created.json()
    rider = auth(client, "rider@example.com", "StrongRiderPassword123!")
    assert client.get("/api/v1/auth/me", headers=rider).json()["role"] == "delivery_partner"


def test_only_admin_can_create_and_list_partners(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    client.post("/api/v1/auth/register", json={"email": "customer@example.com", "full_name": "Customer", "password": "CustomerPassword123!"})
    customer = auth(client, "customer@example.com", "CustomerPassword123!")
    payload = {"email": "rider@example.com", "full_name": "Rider", "password": "StrongRiderPassword123!", "phone": "9876543210"}
    assert client.post("/api/v1/delivery/partners", headers=customer, json=payload).status_code == 403
    assert client.get("/api/v1/delivery/partners", headers=customer).status_code == 403
    assert client.post("/api/v1/delivery/partners", headers=admin, json=payload).status_code == 201


def test_assignment_requires_booking_and_partner_can_update_only_own_delivery(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    customer_registration = client.post("/api/v1/auth/register", json={"email": "owner@example.com", "full_name": "Owner", "password": "CustomerPassword123!"})
    assert customer_registration.status_code == 201
    customer = auth(client, "owner@example.com", "CustomerPassword123!")
    parcel_id = make_parcel(client, customer)
    partner = client.post("/api/v1/delivery/partners", headers=admin, json={
        "email": "rider@example.com", "full_name": "Rider", "password": "StrongRiderPassword123!", "phone": "9876543210",
    }).json()
    no_booking = client.post(f"/api/v1/delivery/parcels/{parcel_id}/assignments", headers=admin, json={"partner_id": partner["id"]})
    assert no_booking.status_code == 409
    book_parcel(client, customer, parcel_id)
    assigned = client.post(f"/api/v1/delivery/parcels/{parcel_id}/assignments", headers=admin, json={"partner_id": partner["id"]})
    assert assigned.status_code == 201
    assert assigned.json()["status"] == "assigned"
    rider = auth(client, "rider@example.com", "StrongRiderPassword123!")
    mine = client.get("/api/v1/delivery/my-assignments", headers=rider)
    assert mine.status_code == 200 and len(mine.json()) == 1
    accepted = client.patch(f"/api/v1/delivery/assignments/{assigned.json()['id']}/status", headers=rider, json={"status": "accepted"})
    assert accepted.status_code == 200
    out = client.patch(f"/api/v1/delivery/assignments/{assigned.json()['id']}/status", headers=rider, json={"status": "out_for_delivery"})
    assert out.status_code == 200
    delivered = client.patch(f"/api/v1/delivery/assignments/{assigned.json()['id']}/status", headers=rider, json={"status": "delivered"})
    assert delivered.status_code == 200
    assert delivered.json()["status"] == "delivered"
    assert client.get(f"/api/v1/delivery/assignments", headers=rider).status_code == 403


def test_partner_cannot_update_another_partners_assignment(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    client.post("/api/v1/auth/register", json={"email": "owner@example.com", "full_name": "Owner", "password": "CustomerPassword123!"})
    customer = auth(client, "owner@example.com", "CustomerPassword123!")
    parcel_id = make_parcel(client, customer)
    book_parcel(client, customer, parcel_id)
    partner = client.post("/api/v1/delivery/partners", headers=admin, json={
        "email": "rider@example.com", "full_name": "Rider", "password": "StrongRiderPassword123!", "phone": "9876543210",
    }).json()
    assignment = client.post(f"/api/v1/delivery/parcels/{parcel_id}/assignments", headers=admin, json={"partner_id": partner["id"]}).json()
    client.post("/api/v1/delivery/partners", headers=admin, json={
        "email": "other@example.com", "full_name": "Other Rider", "password": "StrongOtherPassword123!", "phone": "9876543211",
    })
    other = auth(client, "other@example.com", "StrongOtherPassword123!")
    response = client.patch(f"/api/v1/delivery/assignments/{assignment['id']}/status", headers=other, json={"status": "accepted"})
    assert response.status_code == 404
