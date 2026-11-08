from datetime import date, timedelta

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
    testing_session = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=test_engine)

    db = testing_session()
    db.add(
        User(
            email="admin@example.com",
            full_name="Test Admin",
            password_hash=hash_password("StrongAdminPassword123!"),
            role="admin",
            is_active=True,
        )
    )
    db.commit()
    db.close()

    def override_get_db():
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def register(client, email):
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Test Customer",
            "password": "StrongCustomerPassword123!",
        },
    )


def login(client, email, password):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_registration_creates_customer_and_password_is_not_exposed(client):
    response = register(client, "Customer@Example.com")

    assert response.status_code == 201
    assert response.json()["email"] == "customer@example.com"
    assert response.json()["role"] == "customer"
    assert "password" not in response.json()
    assert "password_hash" not in response.json()


def test_duplicate_email_registration_is_rejected(client):
    assert register(client, "same@example.com").status_code == 201
    assert register(client, "SAME@example.com").status_code == 409


def test_login_and_current_user_endpoint(client):
    register(client, "login@example.com")
    headers = login(client, "login@example.com", "StrongCustomerPassword123!")

    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "login@example.com"
    assert response.json()["role"] == "customer"


def test_protected_endpoints_reject_missing_or_invalid_tokens(client):
    assert client.get("/api/v1/parcels/").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_customer_cannot_create_slots_or_update_parcel_status(client):
    register(client, "customer@example.com")
    customer_headers = login(client, "customer@example.com", "StrongCustomerPassword123!")

    slot_response = client.post(
        "/api/v1/scheduling/slots",
        headers=customer_headers,
        json={
            "delivery_date": (date.today() + timedelta(days=2)).isoformat(),
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "capacity": 2,
        },
    )
    assert slot_response.status_code == 403

    parcel = client.post(
        "/api/v1/parcels/",
        headers=customer_headers,
        json={
            "tracking_number": "TD-AUTH-001",
            "recipient_name": "Customer",
            "phone": "9876543210",
            "address_line": "12 Test Street",
            "city": "Prayagraj",
            "state": "Uttar Pradesh",
            "pincode": "211001",
        },
    )
    assert parcel.status_code == 201

    status_response = client.patch(
        f"/api/v1/parcels/{parcel.json()['id']}/status",
        headers=customer_headers,
        json={"status": "delivered"},
    )
    assert status_response.status_code == 403


def test_customer_cannot_view_another_customers_parcel(client):
    register(client, "owner@example.com")
    register(client, "other@example.com")
    owner_headers = login(client, "owner@example.com", "StrongCustomerPassword123!")
    other_headers = login(client, "other@example.com", "StrongCustomerPassword123!")

    parcel = client.post(
        "/api/v1/parcels/",
        headers=owner_headers,
        json={
            "tracking_number": "TD-OWNER-001",
            "recipient_name": "Parcel Owner",
            "phone": "9876543210",
            "address_line": "12 Test Street",
            "city": "Prayagraj",
            "state": "Uttar Pradesh",
            "pincode": "211001",
        },
    )
    parcel_id = parcel.json()["id"]

    assert client.get(f"/api/v1/parcels/{parcel_id}", headers=owner_headers).status_code == 200
    assert client.get(f"/api/v1/parcels/{parcel_id}", headers=other_headers).status_code == 404
