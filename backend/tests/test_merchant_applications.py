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
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = testing_session()
    db.add(User(email="admin@example.com", full_name="Test Admin",
        password_hash=hash_password("StrongAdminPassword123!"), role="admin", is_active=True))
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
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def admin_headers(client):
    response = client.post("/api/v1/auth/login", json={
        "email": "admin@example.com", "password": "StrongAdminPassword123!"
    })
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def application_payload(email="merchant@example.com"):
    return {
        "email": email,
        "full_name": "Merchant Applicant",
        "password": "StrongMerchantPassword123!",
        "phone_number": "+919876543210",
        "business_name": "Example Traders",
        "business_type": "Retail",
        "pickup_address": "12 Market Road",
        "pickup_city": "Prayagraj",
        "pickup_state": "Uttar Pradesh",
        "pickup_pincode": "211001",
    }


def test_merchant_application_creates_inactive_non_merchant_account(client):
    response = client.post("/api/v1/merchant-applications", json=application_payload())
    assert response.status_code == 201
    assert response.json()["application"]["status"] == "pending"
    login = client.post("/api/v1/auth/login", json={
        "email": "merchant@example.com", "password": "StrongMerchantPassword123!"
    })
    assert login.status_code == 401


def test_only_admin_can_review_and_approve_merchant(client):
    submitted = client.post("/api/v1/merchant-applications", json=application_payload())
    application_id = submitted.json()["application"]["id"]
    assert client.get("/api/v1/operations/merchant-applications").status_code == 401
    headers = admin_headers(client)
    assert client.get("/api/v1/operations/merchant-applications", headers=headers).status_code == 200
    approved = client.post(
        f"/api/v1/operations/merchant-applications/{application_id}/approve",
        headers=headers, json={},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    login = client.post("/api/v1/auth/login", json={
        "email": "merchant@example.com", "password": "StrongMerchantPassword123!"
    })
    assert login.status_code == 200
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    assert me.status_code == 200
    assert me.json()["role"] == "merchant"


def test_rejected_application_cannot_log_in_or_be_approved_again(client):
    submitted = client.post("/api/v1/merchant-applications", json=application_payload())
    application_id = submitted.json()["application"]["id"]
    headers = admin_headers(client)
    rejected = client.post(
        f"/api/v1/operations/merchant-applications/{application_id}/reject",
        headers=headers, json={"reason": "Business details need clarification."},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    repeated = client.post(
        f"/api/v1/operations/merchant-applications/{application_id}/approve",
        headers=headers, json={},
    )
    assert repeated.status_code == 409
    login = client.post("/api/v1/auth/login", json={
        "email": "merchant@example.com", "password": "StrongMerchantPassword123!"
    })
    assert login.status_code == 401


def test_duplicate_merchant_application_is_rejected(client):
    assert client.post("/api/v1/merchant-applications", json=application_payload()).status_code == 201
    duplicate = client.post("/api/v1/merchant-applications", json=application_payload())
    assert duplicate.status_code == 409


def test_suspended_merchant_cannot_log_in_and_can_be_reactivated(client):
    submitted = client.post("/api/v1/merchant-applications", json=application_payload())
    application_id = submitted.json()["application"]["id"]
    headers = admin_headers(client)
    assert client.post(f"/api/v1/operations/merchant-applications/{application_id}/approve",
        headers=headers, json={}).status_code == 200
    suspended = client.post(f"/api/v1/operations/merchant-applications/{application_id}/suspend",
        headers=headers, json={"reason": "Account review."})
    assert suspended.status_code == 200
    assert suspended.json()["status"] == "suspended"
    assert client.post("/api/v1/auth/login", json={
        "email": "merchant@example.com", "password": "StrongMerchantPassword123!"
    }).status_code == 401
    reactivated = client.post(f"/api/v1/operations/merchant-applications/{application_id}/reactivate",
        headers=headers, json={})
    assert reactivated.status_code == 200
    assert reactivated.json()["status"] == "approved"
    assert client.post("/api/v1/auth/login", json={
        "email": "merchant@example.com", "password": "StrongMerchantPassword123!"
    }).status_code == 200
