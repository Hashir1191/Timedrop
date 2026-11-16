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
def journey_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    with sessions() as db:
        db.add(User(
            email="journey-ops@example.com",
            full_name="Journey Operations",
            password_hash=hash_password("StrongJourneyOpsPassword123!"),
            role="admin",
        ))
        db.add(ServiceablePincode(
            pincode="211001",
            city="Prayagraj",
            state="Uttar Pradesh",
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
        yield client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _login(client, email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_customer_to_partner_delivery_journey_is_visible_across_portals(journey_client):
    client = journey_client
    admin = _login(client, "journey-ops@example.com", "StrongJourneyOpsPassword123!")

    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "journey-customer@example.com",
            "full_name": "Journey Customer",
            "password": "StrongJourneyCustomerPassword123!",
        },
    )
    assert registration.status_code == 201, registration.text
    customer = _login(client, "journey-customer@example.com", "StrongJourneyCustomerPassword123!")

    parcel_response = client.post(
        "/api/v1/parcels/",
        headers=customer,
        json={
            "tracking_number": "TD-E2E-2026-001",
            "recipient_name": "Synthetic Recipient",
            "phone": "9876543210",
            "address_line": "12 Integration Test Road",
            "city": "Prayagraj",
            "state": "Uttar Pradesh",
            "pincode": "211001",
        },
    )
    assert parcel_response.status_code == 201, parcel_response.text
    parcel_id = parcel_response.json()["id"]

    slot_response = client.post(
        "/api/v1/scheduling/slots",
        headers=admin,
        json={
            "delivery_date": (date.today() + timedelta(days=5)).isoformat(),
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "capacity": 2,
        },
    )
    assert slot_response.status_code == 201, slot_response.text
    slot_id = slot_response.json()["id"]

    booking_response = client.post(
        f"/api/v1/scheduling/parcels/{parcel_id}/bookings",
        headers=customer,
        json={"slot_id": slot_id},
    )
    assert booking_response.status_code == 201, booking_response.text

    partner_response = client.post(
        "/api/v1/delivery/partners",
        headers=admin,
        json={
            "email": "journey-rider@example.com",
            "full_name": "Journey Rider",
            "password": "StrongJourneyRiderPassword123!",
            "phone": "9876543211",
            "vehicle_type": "two_wheeler",
        },
    )
    assert partner_response.status_code == 201, partner_response.text
    partner_id = partner_response.json()["id"]
    rider = _login(client, "journey-rider@example.com", "StrongJourneyRiderPassword123!")

    assignment_response = client.post(
        f"/api/v1/delivery/parcels/{parcel_id}/assignments",
        headers=admin,
        json={"partner_id": partner_id},
    )
    assert assignment_response.status_code == 201, assignment_response.text
    assignment_id = assignment_response.json()["id"]

    inbox = client.get("/api/v1/delivery/my-assignments", headers=rider)
    assert inbox.status_code == 200, inbox.text
    assert [item["id"] for item in inbox.json()] == [assignment_id]

    accepted = client.patch(
        f"/api/v1/delivery/assignments/{assignment_id}/status",
        headers=rider,
        json={"status": "accepted"},
    )
    assert accepted.status_code == 200, accepted.text

    out_for_delivery = client.patch(
        f"/api/v1/delivery/assignments/{assignment_id}/status",
        headers=rider,
        json={"status": "out_for_delivery"},
    )
    assert out_for_delivery.status_code == 200, out_for_delivery.text

    code_response = client.post(
        f"/api/v1/delivery/parcels/{parcel_id}/delivery-code",
        headers=customer,
    )
    assert code_response.status_code == 200, code_response.text
    assert len(code_response.json()["code"]) == 6

    proof_response = client.post(
        f"/api/v1/delivery/assignments/{assignment_id}/proof",
        headers=rider,
        json={
            "code": code_response.json()["code"],
            "recipient_name": "Synthetic Recipient",
        },
    )
    assert proof_response.status_code == 200, proof_response.text
    assert proof_response.json()["status"] == "delivered"

    customer_parcels = client.get("/api/v1/parcels/", headers=customer)
    assert customer_parcels.status_code == 200
    assert [item["id"] for item in customer_parcels.json()] == [parcel_id]

    timeline = client.get(f"/api/v1/parcels/{parcel_id}/timeline", headers=customer)
    assert timeline.status_code == 200, timeline.text
    timeline_titles = [event["title"] for event in timeline.json()]
    assert "Parcel registered" in timeline_titles
    assert "Delivery slot booked" in timeline_titles
    assert "Delivery partner assigned" in timeline_titles
    assert "Parcel is out for delivery" in timeline_titles
    assert "Parcel delivered" in timeline_titles

    delivery_events = client.get(
        f"/api/v1/delivery/assignments/{assignment_id}/events",
        headers=customer,
    )
    assert delivery_events.status_code == 200, delivery_events.text
    delivery_event_rows = delivery_events.json()
    event_types = {event["event_type"] for event in delivery_event_rows}
    status_transitions = {event["to_status"] for event in delivery_event_rows}
    assert {"assigned", "status_changed", "proof_of_delivery"}.issubset(event_types)
    assert {"accepted", "out_for_delivery", "delivered"}.issubset(status_transitions)

    notifications = client.get("/api/v1/notifications/?limit=100", headers=customer)
    assert notifications.status_code == 200, notifications.text
    notification_types = {item["event_type"] for item in notifications.json()}
    assert {
        "booking_created",
        "delivery_partner_assigned",
        "delivery_accepted",
        "delivery_out_for_delivery",
        "delivery_completed",
    }.issubset(notification_types)

    unread = client.get("/api/v1/notifications/unread-count", headers=customer)
    assert unread.status_code == 200
    assert unread.json()["unread_count"] >= 1

    read_all = client.post("/api/v1/notifications/read-all", headers=customer)
    assert read_all.status_code == 200
    assert read_all.json()["updated_count"] >= 1
    assert client.get("/api/v1/notifications/unread-count", headers=customer).json()["unread_count"] == 0

    assert client.get(f"/api/v1/delivery/assignments", headers=rider).status_code == 403


def test_customer_cannot_read_another_customers_parcel_journey(journey_client):
    client = journey_client
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "journey-owner@example.com",
            "full_name": "Parcel Owner",
            "password": "StrongJourneyOwnerPassword123!",
        },
    )
    owner = _login(client, "journey-owner@example.com", "StrongJourneyOwnerPassword123!")
    parcel = client.post(
        "/api/v1/parcels/",
        headers=owner,
        json={
            "tracking_number": "TD-E2E-PRIVATE-001",
            "recipient_name": "Private Recipient",
            "phone": "9876543210",
            "address_line": "15 Private Test Road",
            "city": "Prayagraj",
            "state": "Uttar Pradesh",
            "pincode": "211001",
        },
    )
    assert parcel.status_code == 201, parcel.text

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "journey-other@example.com",
            "full_name": "Other Customer",
            "password": "StrongJourneyOtherPassword123!",
        },
    )
    other = _login(client, "journey-other@example.com", "StrongJourneyOtherPassword123!")

    response = client.get(
        f"/api/v1/parcels/{parcel.json()['id']}/timeline",
        headers=other,
    )

    assert response.status_code == 404
