from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import DeliveryAssignment, DeliveryPartner, Parcel, User
from app.security import hash_password


@pytest.fixture()
def analytics_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = sessions()
    admin = User(email="analytics-admin@example.com", full_name="Analytics Admin",
                 password_hash=hash_password("StrongAdminPassword123!"), role="admin")
    partner_user = User(email="analytics-partner@example.com", full_name="Asha Rider",
                        password_hash=hash_password("StrongPartnerPassword123!"), role="delivery_partner")
    customer = User(email="analytics-customer@example.com", full_name="Analytics Customer",
                    password_hash=hash_password("StrongCustomerPassword123!"), role="customer")
    db.add_all([admin, partner_user, customer])
    db.flush()
    partner = DeliveryPartner(user_id=partner_user.id, phone="9876543210", vehicle_type="two_wheeler")
    db.add(partner)
    db.flush()

    assigned_at = datetime(2026, 11, 10, 8, 0, tzinfo=timezone.utc)
    delivered_at = datetime(2026, 11, 10, 10, 30, tzinfo=timezone.utc)
    parcel_delivered = Parcel(
        owner_id=customer.id, tracking_number="TD-ANALYTICS-DELIVERED",
        recipient_name="Recipient One", phone="9876543211", address_line="1 Analytics Road",
        city="Prayagraj", state="Uttar Pradesh", pincode="211001",
        created_at=datetime(2026, 11, 9, 8, 0, tzinfo=timezone.utc), status="delivered",
    )
    parcel_failed = Parcel(
        owner_id=customer.id, tracking_number="TD-ANALYTICS-FAILED",
        recipient_name="Recipient Two", phone="9876543212", address_line="2 Analytics Road",
        city="Prayagraj", state="Uttar Pradesh", pincode="211002",
        created_at=datetime(2026, 11, 9, 9, 0, tzinfo=timezone.utc), status="failed",
    )
    db.add_all([parcel_delivered, parcel_failed])
    db.flush()
    db.add_all([
        DeliveryAssignment(
            parcel_id=parcel_delivered.id, partner_id=partner.id, status="delivered",
            assigned_at=assigned_at, delivered_at=delivered_at, updated_at=delivered_at,
        ),
        DeliveryAssignment(
            parcel_id=parcel_failed.id, partner_id=partner.id, status="failed",
            assigned_at=datetime(2026, 11, 11, 8, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc),
        ),
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
    with TestClient(app) as client:
        admin_login = client.post("/api/v1/auth/login", json={
            "email": "analytics-admin@example.com", "password": "StrongAdminPassword123!",
        })
        customer_login = client.post("/api/v1/auth/login", json={
            "email": "analytics-customer@example.com", "password": "StrongCustomerPassword123!",
        })
        assert admin_login.status_code == 200
        assert customer_login.status_code == 200
        yield client, {
            "admin": {"Authorization": f"Bearer {admin_login.json()['access_token']}"},
            "customer": {"Authorization": f"Bearer {customer_login.json()['access_token']}"},
        }

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_admin_analytics_returns_delivery_kpis_and_partner_performance(analytics_client):
    client, headers = analytics_client
    response = client.get(
        "/api/v1/operations/analytics?start_date=2026-11-01&end_date=2026-11-30",
        headers=headers["admin"],
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["parcels_created"] == 2
    assert payload["assignments_created"] == 2
    assert payload["delivered"] == 1
    assert payload["failed"] == 1
    assert payload["active"] == 0
    assert payload["success_rate"] == 50.0
    assert payload["average_delivery_hours"] == 2.5
    assert payload["partner_count"] == 1
    assert payload["partners"][0]["partner_name"] == "Asha Rider"
    assert payload["partners"][0]["success_rate"] == 50.0
    daily = {row["day"]: row for row in payload["daily"]}
    assert daily["2026-11-10"]["delivered"] == 1
    assert daily["2026-11-11"]["failed"] == 1


def test_analytics_is_admin_only_and_rejects_invalid_date_range(analytics_client):
    client, headers = analytics_client
    forbidden = client.get("/api/v1/operations/analytics", headers=headers["customer"])
    assert forbidden.status_code == 403

    invalid = client.get(
        "/api/v1/operations/analytics?start_date=2026-11-20&end_date=2026-11-01",
        headers=headers["admin"],
    )
    assert invalid.status_code == 422
