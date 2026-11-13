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
    issued = client.post(f"/api/v1/delivery/parcels/{parcel_id}/delivery-code", headers=customer)
    assert issued.status_code == 200
    delivered = client.post(
        f"/api/v1/delivery/assignments/{assigned.json()['id']}/proof",
        headers=rider,
        json={"code": issued.json()["code"], "recipient_name": "Owner"},
    )
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

def test_failed_delivery_requires_and_persists_reason(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    client.post("/api/v1/auth/register", json={"email": "failure-owner@example.com", "full_name": "Owner", "password": "CustomerPassword123!"})
    customer = auth(client, "failure-owner@example.com", "CustomerPassword123!")
    parcel_id = make_parcel(client, customer, "TD-PARTNER-FAIL-001")
    book_parcel(client, customer, parcel_id)
    partner = client.post("/api/v1/delivery/partners", headers=admin, json={
        "email": "failure-rider@example.com", "full_name": "Failure Rider",
        "password": "StrongRiderPassword123!", "phone": "9876543210",
    }).json()
    assignment = client.post(
        f"/api/v1/delivery/parcels/{parcel_id}/assignments",
        headers=admin, json={"partner_id": partner["id"]},
    ).json()
    rider = auth(client, "failure-rider@example.com", "StrongRiderPassword123!")
    missing_reason = client.patch(
        f"/api/v1/delivery/assignments/{assignment['id']}/status",
        headers=rider, json={"status": "failed"},
    )
    assert missing_reason.status_code == 422
    failed = client.patch(
        f"/api/v1/delivery/assignments/{assignment['id']}/status",
        headers=rider, json={"status": "failed", "failure_reason": "Recipient unavailable"},
    )
    assert failed.status_code == 200
    assert failed.json()["failure_reason"] == "Recipient unavailable"


def test_customer_cannot_change_booking_after_active_partner_assignment(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    client.post("/api/v1/auth/register", json={
        "email": "locked-owner@example.com",
        "full_name": "Booking Owner",
        "password": "CustomerPassword123!",
    })
    customer = auth(client, "locked-owner@example.com", "CustomerPassword123!")
    parcel_id = make_parcel(client, customer, "TD-PARTNER-LOCK-001")
    book_parcel(client, customer, parcel_id)

    partner_response = client.post("/api/v1/delivery/partners", headers=admin, json={
        "email": "locked-rider@example.com",
        "full_name": "Locked Rider",
        "password": "StrongRiderPassword123!",
        "phone": "9876543210",
    })
    assert partner_response.status_code == 201
    assigned = client.post(
        f"/api/v1/delivery/parcels/{parcel_id}/assignments",
        headers=admin,
        json={"partner_id": partner_response.json()["id"]},
    )
    assert assigned.status_code == 201

    cancelled = client.delete(
        f"/api/v1/scheduling/parcels/{parcel_id}/bookings",
        headers=customer,
    )
    assert cancelled.status_code == 409

    replacement_slot = client.post(
        "/api/v1/scheduling/slots",
        headers=admin,
        json={
            "delivery_date": (datetime.now().date() + timedelta(days=4)).isoformat(),
            "start_time": "13:00:00",
            "end_time": "15:00:00",
            "capacity": 5,
        },
    )
    assert replacement_slot.status_code == 201
    rescheduled = client.patch(
        f"/api/v1/scheduling/parcels/{parcel_id}/bookings",
        headers=customer,
        json={"slot_id": replacement_slot.json()["id"]},
    )
    assert rescheduled.status_code == 409

    active = client.get("/api/v1/delivery/assignments", headers=admin)
    assert active.status_code == 200
    assert any(item["parcel_id"] == parcel_id and item["status"] == "assigned" for item in active.json())


def test_delivery_event_history_is_ordered_and_access_controlled(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    assert client.post("/api/v1/auth/register", json={
        "email": "history-owner@example.com", "full_name": "History Owner",
        "password": "CustomerPassword123!",
    }).status_code == 201
    assert client.post("/api/v1/auth/register", json={
        "email": "history-other@example.com", "full_name": "Other Customer",
        "password": "CustomerPassword123!",
    }).status_code == 201
    customer = auth(client, "history-owner@example.com", "CustomerPassword123!")
    other = auth(client, "history-other@example.com", "CustomerPassword123!")
    parcel_id = make_parcel(client, customer, "TD-HISTORY-001")
    book_parcel(client, customer, parcel_id)
    partner_response = client.post("/api/v1/delivery/partners", headers=admin, json={
        "email": "history-rider@example.com", "full_name": "History Rider",
        "password": "StrongRiderPassword123!", "phone": "9876543210",
    })
    assert partner_response.status_code == 201
    assignment = client.post(
        f"/api/v1/delivery/parcels/{parcel_id}/assignments",
        headers=admin, json={"partner_id": partner_response.json()["id"]},
    )
    assert assignment.status_code == 201
    assignment_id = assignment.json()["id"]
    path = f"/api/v1/delivery/assignments/{assignment_id}/events"
    rider = auth(client, "history-rider@example.com", "StrongRiderPassword123!")
    assert client.get(path, headers=other).status_code == 404
    assert client.get(path).status_code in (401, 403)
    for state in ("accepted", "out_for_delivery"):
        response = client.patch(
            f"/api/v1/delivery/assignments/{assignment_id}/status",
            headers=rider, json={"status": state},
        )
        assert response.status_code == 200
    issued = client.post(f"/api/v1/delivery/parcels/{parcel_id}/delivery-code", headers=customer)
    assert issued.status_code == 200
    delivered = client.post(
        f"/api/v1/delivery/assignments/{assignment_id}/proof",
        headers=rider,
        json={"code": issued.json()["code"], "recipient_name": "History Owner"},
    )
    assert delivered.status_code == 200
    for headers in (admin, customer, rider):
        response = client.get(path, headers=headers)
        assert response.status_code == 200
        events = response.json()
        assert [event["event_type"] for event in events] == [
            "assigned", "status_changed", "status_changed", "delivery_code_issued", "proof_of_delivery",
        ]
        assert [event["to_status"] for event in events] == [
            "assigned", "accepted", "out_for_delivery", "out_for_delivery", "delivered",
        ]
        assert events[0]["actor_name"] == "Ops"
        assert events[-1]["actor_name"] == "History Rider"
        assert all(event["parcel_id"] == parcel_id for event in events)


def test_delivery_failure_reason_is_preserved_in_event_history(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    assert client.post("/api/v1/auth/register", json={
        "email": "event-fail-owner@example.com", "full_name": "Event Owner",
        "password": "CustomerPassword123!",
    }).status_code == 201
    customer = auth(client, "event-fail-owner@example.com", "CustomerPassword123!")
    parcel_id = make_parcel(client, customer, "TD-HISTORY-FAIL")
    book_parcel(client, customer, parcel_id)
    partner = client.post("/api/v1/delivery/partners", headers=admin, json={
        "email": "event-fail-rider@example.com", "full_name": "Event Rider",
        "password": "StrongRiderPassword123!", "phone": "9876543210",
    })
    assert partner.status_code == 201
    assigned = client.post(
        f"/api/v1/delivery/parcels/{parcel_id}/assignments",
        headers=admin, json={"partner_id": partner.json()["id"]},
    )
    assert assigned.status_code == 201
    rider = auth(client, "event-fail-rider@example.com", "StrongRiderPassword123!")
    assignment_id = assigned.json()["id"]
    response = client.patch(
        f"/api/v1/delivery/assignments/{assignment_id}/status",
        headers=rider, json={"status": "failed", "failure_reason": "Recipient unavailable"},
    )
    assert response.status_code == 200
    events = client.get(f"/api/v1/delivery/assignments/{assignment_id}/events", headers=customer)
    assert events.status_code == 200
    assert events.json()[-1]["note"] == "Recipient unavailable"


def test_delivery_requires_customer_code_and_records_proof(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    client.post("/api/v1/auth/register", json={
        "email": "pod-owner@example.com", "full_name": "Parcel Owner",
        "password": "CustomerPassword123!",
    })
    client.post("/api/v1/auth/register", json={
        "email": "pod-other@example.com", "full_name": "Other Owner",
        "password": "CustomerPassword123!",
    })
    customer = auth(client, "pod-owner@example.com", "CustomerPassword123!")
    other = auth(client, "pod-other@example.com", "CustomerPassword123!")
    parcel_id = make_parcel(client, customer, "TD-POD-001")
    book_parcel(client, customer, parcel_id)
    partner = client.post("/api/v1/delivery/partners", headers=admin, json={
        "email": "pod-rider@example.com", "full_name": "POD Rider",
        "password": "StrongRiderPassword123!", "phone": "9876543210",
    }).json()
    assignment = client.post(
        f"/api/v1/delivery/parcels/{parcel_id}/assignments",
        headers=admin, json={"partner_id": partner["id"]},
    ).json()
    rider = auth(client, "pod-rider@example.com", "StrongRiderPassword123!")
    assignment_id = assignment["id"]

    premature = client.post(
        f"/api/v1/delivery/assignments/{assignment_id}/proof",
        headers=rider, json={"code": "123456", "recipient_name": "Parcel Owner"},
    )
    assert premature.status_code == 409

    for state in ("accepted", "out_for_delivery"):
        response = client.patch(
            f"/api/v1/delivery/assignments/{assignment_id}/status",
            headers=rider, json={"status": state},
        )
        assert response.status_code == 200

    code_path = f"/api/v1/delivery/parcels/{parcel_id}/delivery-code"
    assert client.post(code_path, headers=other).status_code == 404
    issued = client.post(code_path, headers=customer)
    assert issued.status_code == 200
    assert len(issued.json()["code"]) == 6
    assert "delivery_code_hash" not in issued.json()

    bypass = client.patch(
        f"/api/v1/delivery/assignments/{assignment_id}/status",
        headers=rider, json={"status": "delivered"},
    )
    assert bypass.status_code == 409

    wrong = client.post(
        f"/api/v1/delivery/assignments/{assignment_id}/proof",
        headers=rider, json={"code": "000000", "recipient_name": "Parcel Owner"},
    )
    if issued.json()["code"] != "000000":
        assert wrong.status_code == 400

    verified = client.post(
        f"/api/v1/delivery/assignments/{assignment_id}/proof",
        headers=rider,
        json={"code": issued.json()["code"], "recipient_name": "Parcel Owner"},
    )
    assert verified.status_code == 200
    assert verified.json()["status"] == "delivered"

    duplicate = client.post(
        f"/api/v1/delivery/assignments/{assignment_id}/proof",
        headers=rider,
        json={"code": issued.json()["code"], "recipient_name": "Parcel Owner"},
    )
    assert duplicate.status_code == 409

    history = client.get(
        f"/api/v1/delivery/assignments/{assignment_id}/events",
        headers=customer,
    )
    assert history.status_code == 200
    assert history.json()[-1]["event_type"] == "proof_of_delivery"
    assert "Parcel Owner" in history.json()[-1]["note"]


def test_delivery_code_locks_after_five_incorrect_attempts(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    client.post("/api/v1/auth/register", json={
        "email": "pod-lock-owner@example.com", "full_name": "Lock Owner",
        "password": "CustomerPassword123!",
    })
    customer = auth(client, "pod-lock-owner@example.com", "CustomerPassword123!")
    parcel_id = make_parcel(client, customer, "TD-POD-LOCK")
    book_parcel(client, customer, parcel_id)
    partner = client.post("/api/v1/delivery/partners", headers=admin, json={
        "email": "pod-lock-rider@example.com", "full_name": "Lock Rider",
        "password": "StrongRiderPassword123!", "phone": "9876543210",
    }).json()
    assignment = client.post(
        f"/api/v1/delivery/parcels/{parcel_id}/assignments",
        headers=admin, json={"partner_id": partner["id"]},
    ).json()
    rider = auth(client, "pod-lock-rider@example.com", "StrongRiderPassword123!")
    assignment_id = assignment["id"]
    for state in ("accepted", "out_for_delivery"):
        assert client.patch(
            f"/api/v1/delivery/assignments/{assignment_id}/status",
            headers=rider, json={"status": state},
        ).status_code == 200
    issued = client.post(f"/api/v1/delivery/parcels/{parcel_id}/delivery-code", headers=customer)
    assert issued.status_code == 200
    wrong_code = "000000" if issued.json()["code"] != "000000" else "999999"
    for attempt in range(5):
        response = client.post(
            f"/api/v1/delivery/assignments/{assignment_id}/proof",
            headers=rider, json={"code": wrong_code, "recipient_name": "Lock Owner"},
        )
        assert response.status_code == 400
    blocked = client.post(
        f"/api/v1/delivery/assignments/{assignment_id}/proof",
        headers=rider, json={"code": issued.json()["code"], "recipient_name": "Lock Owner"},
    )
    assert blocked.status_code == 409



def test_partner_capacity_is_enforced_and_route_plan_respects_limit(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    assert client.post("/api/v1/auth/register", json={
        "email": "capacity-owner@example.com", "full_name": "Capacity Owner",
        "password": "CustomerPassword123!",
    }).status_code == 201
    customer = auth(client, "capacity-owner@example.com", "CustomerPassword123!")

    first_id = make_parcel(client, customer, "TD-CAPACITY-001")
    second_id = make_parcel(client, customer, "TD-CAPACITY-002")
    delivery_date = (datetime.now().date() + timedelta(days=3)).isoformat()
    slot = client.post("/api/v1/scheduling/slots", headers=admin, json={
        "delivery_date": delivery_date, "start_time": "10:00:00",
        "end_time": "12:00:00", "capacity": 5,
    })
    assert slot.status_code == 201
    for parcel_id in (first_id, second_id):
        booked = client.post(
            f"/api/v1/scheduling/parcels/{parcel_id}/bookings",
            headers=customer, json={"slot_id": slot.json()["id"]},
        )
        assert booked.status_code == 201

    partner_response = client.post("/api/v1/delivery/partners", headers=admin, json={
        "email": "capacity-rider@example.com", "full_name": "Capacity Rider",
        "password": "StrongRiderPassword123!", "phone": "9876543210",
        "max_active_assignments": 1,
    })
    assert partner_response.status_code == 201
    partner = partner_response.json()
    assert partner["max_active_assignments"] == 1

    first_assignment = client.post(
        f"/api/v1/delivery/parcels/{first_id}/assignments",
        headers=admin, json={"partner_id": partner["id"]},
    )
    assert first_assignment.status_code == 201

    second_assignment = client.post(
        f"/api/v1/delivery/parcels/{second_id}/assignments",
        headers=admin, json={"partner_id": partner["id"]},
    )
    assert second_assignment.status_code == 409
    assert "capacity" in second_assignment.json()["detail"].lower()

    plan = client.get(f"/api/v1/delivery/route-plan?delivery_date={delivery_date}", headers=admin)
    assert plan.status_code == 200
    assert plan.json()["recommended"] == 0
    assert plan.json()["unassigned_without_partner"] == 1
    assert plan.json()["stops"][0]["suggested_partner_id"] is None



def test_assignment_notifications_have_role_appropriate_action_destinations(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    assert client.post("/api/v1/auth/register", json={
        "email": "action-owner@example.com", "full_name": "Action Owner",
        "password": "CustomerPassword123!",
    }).status_code == 201
    customer = auth(client, "action-owner@example.com", "CustomerPassword123!")
    parcel_id = make_parcel(client, customer, "TD-ACTION-LINK-001")
    book_parcel(client, customer, parcel_id)
    partner_response = client.post("/api/v1/delivery/partners", headers=admin, json={
        "email": "action-rider@example.com", "full_name": "Action Rider",
        "password": "StrongRiderPassword123!", "phone": "9876543210",
    })
    assert partner_response.status_code == 201
    partner = auth(client, "action-rider@example.com", "StrongRiderPassword123!")
    assigned = client.post(
        f"/api/v1/delivery/parcels/{parcel_id}/assignments",
        headers=admin, json={"partner_id": partner_response.json()["id"]},
    )
    assert assigned.status_code == 201
    customer_notifications = client.get("/api/v1/notifications/", headers=customer)
    partner_notifications = client.get("/api/v1/notifications/", headers=partner)
    assert customer_notifications.status_code == 200
    assert partner_notifications.status_code == 200
    customer_assignment = next(item for item in customer_notifications.json() if item["event_type"] == "delivery_partner_assigned")
    partner_assignment = next(item for item in partner_notifications.json() if item["event_type"] == "new_delivery_assignment")
    assert customer_assignment["action_url"] == f"/my-parcels?parcelId={parcel_id}"
    assert partner_assignment["action_url"] == "/"
    assert client.patch(f"/api/v1/notifications/{partner_assignment['id']}/read", headers=customer).status_code == 404


def test_partner_can_manage_own_weekly_availability_and_admin_can_view(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    created = client.post("/api/v1/delivery/partners", headers=admin, json={
        "email": "schedule-rider@example.com", "full_name": "Schedule Rider",
        "password": "StrongSchedulePassword123!", "phone": "9876543210",
    })
    assert created.status_code == 201
    rider = auth(client, "schedule-rider@example.com", "StrongSchedulePassword123!")
    weekday = (datetime.now().date() + timedelta(days=3)).weekday()
    payload = {
        "enabled": True,
        "windows": [
            {"weekday": weekday, "start_time": "09:00:00", "end_time": "13:00:00"},
            {"weekday": weekday, "start_time": "14:00:00", "end_time": "17:00:00"},
        ],
    }
    saved = client.put("/api/v1/delivery/my-availability", headers=rider, json=payload)
    assert saved.status_code == 200
    assert saved.json()["enabled"] is True
    assert len(saved.json()["windows"]) == 2
    viewed = client.get(
        f"/api/v1/delivery/partners/{created.json()['id']}/availability",
        headers=admin,
    )
    assert viewed.status_code == 200
    assert viewed.json() == saved.json()


def test_partner_availability_rejects_overlapping_windows(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    client.post("/api/v1/delivery/partners", headers=admin, json={
        "email": "overlap-rider@example.com", "full_name": "Overlap Rider",
        "password": "StrongOverlapPassword123!", "phone": "9876543210",
    })
    rider = auth(client, "overlap-rider@example.com", "StrongOverlapPassword123!")
    response = client.put("/api/v1/delivery/my-availability", headers=rider, json={
        "enabled": True,
        "windows": [
            {"weekday": 2, "start_time": "09:00:00", "end_time": "12:00:00"},
            {"weekday": 2, "start_time": "11:00:00", "end_time": "13:00:00"},
        ],
    })
    assert response.status_code == 422


def test_assignment_must_fit_inside_enabled_partner_availability(client):
    admin = auth(client, "ops@example.com", "StrongAdminPassword123!")
    client.post("/api/v1/auth/register", json={
        "email": "schedule-owner@example.com", "full_name": "Owner",
        "password": "CustomerPassword123!",
    })
    customer = auth(client, "schedule-owner@example.com", "CustomerPassword123!")
    parcel_id = make_parcel(client, customer, "TD-PARTNER-SCHEDULE-001")
    book_parcel(client, customer, parcel_id)
    partner = client.post("/api/v1/delivery/partners", headers=admin, json={
        "email": "restricted-rider@example.com", "full_name": "Restricted Rider",
        "password": "StrongRestrictedPassword123!", "phone": "9876543210",
    }).json()
    rider = auth(client, "restricted-rider@example.com", "StrongRestrictedPassword123!")
    weekday = (datetime.now().date() + timedelta(days=3)).weekday()
    configured = client.put("/api/v1/delivery/my-availability", headers=rider, json={
        "enabled": True,
        "windows": [
            {"weekday": weekday, "start_time": "11:00:00", "end_time": "13:00:00"},
        ],
    })
    assert configured.status_code == 200
    rejected = client.post(
        f"/api/v1/delivery/parcels/{parcel_id}/assignments",
        headers=admin,
        json={"partner_id": partner["id"]},
    )
    assert rejected.status_code == 409
    assert "not available" in rejected.json()["detail"]
