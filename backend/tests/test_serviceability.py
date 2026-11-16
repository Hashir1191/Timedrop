import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.security import hash_password


def auth(client, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def parcel_payload(tracking="TD-SERVICEABILITY-001", pincode="211001"):
    return {
        "tracking_number": tracking,
        "recipient_name": "Synthetic Recipient",
        "phone": "9876543210",
        "address_line": "12 Example Test Street",
        "city": "Prayagraj",
        "state": "Uttar Pradesh",
        "pincode": pincode,
    }


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = sessions()
    db.add(User(
        email="service-ops@example.com",
        full_name="Service Operations",
        password_hash=hash_password("StrongServiceAdminPassword123!"),
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


def test_public_serviceability_lookup_and_admin_deactivation(client):
    admin = auth(client, "service-ops@example.com", "StrongServiceAdminPassword123!")
    unknown = client.get("/api/v1/serviceability/211001")
    assert unknown.status_code == 200
    assert unknown.json()["serviceable"] is False

    created = client.post(
        "/api/v1/operations/service-areas/",
        headers=admin,
        json={"pincode": "211001", "city": "Prayagraj", "state": "Uttar Pradesh"},
    )
    assert created.status_code == 201
    assert created.json()["is_active"] is True

    supported = client.get("/api/v1/serviceability/211001")
    assert supported.status_code == 200
    assert supported.json()["serviceable"] is True
    assert supported.json()["city"] == "Prayagraj"

    paused = client.patch(
        f"/api/v1/operations/service-areas/{created.json()['id']}",
        headers=admin,
        json={"is_active": False},
    )
    assert paused.status_code == 200
    assert paused.json()["is_active"] is False
    assert client.get("/api/v1/serviceability/211001").json()["serviceable"] is False


def test_customer_parcel_creation_requires_active_service_area(client):
    client.post("/api/v1/auth/register", json={
        "email": "service-customer@example.com",
        "full_name": "Service Customer",
        "password": "StrongCustomerPassword123!",
    })
    customer = auth(client, "service-customer@example.com", "StrongCustomerPassword123!")

    rejected = client.post("/api/v1/parcels/", headers=customer, json=parcel_payload())
    assert rejected.status_code == 409
    assert "does not currently serve PIN code" in rejected.json()["detail"]

    admin = auth(client, "service-ops@example.com", "StrongServiceAdminPassword123!")
    created = client.post(
        "/api/v1/operations/service-areas/",
        headers=admin,
        json={"pincode": "211001", "city": "Prayagraj", "state": "Uttar Pradesh"},
    )
    assert created.status_code == 201

    accepted = client.post("/api/v1/parcels/", headers=customer, json=parcel_payload())
    assert accepted.status_code == 201
    assert accepted.json()["pincode"] == "211001"

    client.patch(
        f"/api/v1/operations/service-areas/{created.json()['id']}",
        headers=admin,
        json={"is_active": False},
    )
    blocked_after_deactivation = client.post(
        "/api/v1/parcels/",
        headers=customer,
        json=parcel_payload("TD-SERVICEABILITY-002"),
    )
    assert blocked_after_deactivation.status_code == 409


def test_only_admin_can_manage_service_areas_and_duplicate_pincodes_are_rejected(client):
    client.post("/api/v1/auth/register", json={
        "email": "service-customer-two@example.com",
        "full_name": "Service Customer",
        "password": "StrongCustomerPassword123!",
    })
    customer = auth(client, "service-customer-two@example.com", "StrongCustomerPassword123!")
    payload = {"pincode": "211001", "city": "Prayagraj", "state": "Uttar Pradesh"}

    assert client.get("/api/v1/operations/service-areas/", headers=customer).status_code == 403
    assert client.post("/api/v1/operations/service-areas/", headers=customer, json=payload).status_code == 403

    admin = auth(client, "service-ops@example.com", "StrongServiceAdminPassword123!")
    assert client.post("/api/v1/operations/service-areas/", headers=admin, json=payload).status_code == 201
    duplicate = client.post("/api/v1/operations/service-areas/", headers=admin, json=payload)
    assert duplicate.status_code == 409
    assert client.get("/api/v1/serviceability/012345").status_code == 422


def test_parcel_registration_normalizes_text_and_rejects_invalid_contact_data(client):
    client.post("/api/v1/auth/register", json={
        "email": "parcel-validation@example.com",
        "full_name": "Parcel Validation",
        "password": "StrongCustomerPassword123!",
    })
    customer = auth(client, "parcel-validation@example.com", "StrongCustomerPassword123!")
    admin = auth(client, "service-ops@example.com", "StrongServiceAdminPassword123!")
    area = client.post(
        "/api/v1/operations/service-areas/",
        headers=admin,
        json={"pincode": "211001", "city": "Prayagraj", "state": "Uttar Pradesh"},
    )
    assert area.status_code == 201

    normalized = parcel_payload("  TD-VALIDATION-001  ")
    normalized.update({
        "recipient_name": "  Synthetic   Recipient  ",
        "address_line": "  12   Example   Test Street ",
        "city": "  Prayagraj  ",
        "state": " Uttar   Pradesh ",
        "phone": " +91 (98765) 43210 ",
        "delivery_instructions": "  Leave   at   reception  ",
    })
    created = client.post("/api/v1/parcels/", headers=customer, json=normalized)
    assert created.status_code == 201, created.text
    result = created.json()
    assert result["tracking_number"] == "TD-VALIDATION-001"
    assert result["recipient_name"] == "Synthetic Recipient"
    assert result["address_line"] == "12 Example Test Street"
    assert result["city"] == "Prayagraj"
    assert result["state"] == "Uttar Pradesh"
    assert result["phone"] == "+91 (98765) 43210"
    assert result["delivery_instructions"] == "Leave at reception"

    blank_recipient = parcel_payload("TD-VALIDATION-002")
    blank_recipient["recipient_name"] = "   "
    rejected_name = client.post("/api/v1/parcels/", headers=customer, json=blank_recipient)
    assert rejected_name.status_code == 422

    invalid_phone = parcel_payload("TD-VALIDATION-003")
    invalid_phone["phone"] = "call me maybe"
    rejected_phone = client.post("/api/v1/parcels/", headers=customer, json=invalid_phone)
    assert rejected_phone.status_code == 422

    short_phone = parcel_payload("TD-VALIDATION-004")
    short_phone["phone"] = "123456789"
    rejected_short_phone = client.post("/api/v1/parcels/", headers=customer, json=short_phone)
    assert rejected_short_phone.status_code == 422
