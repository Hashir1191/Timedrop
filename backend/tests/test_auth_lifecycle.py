from collections.abc import Iterator

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
def auth_client() -> Iterator[tuple[TestClient, sessionmaker]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    with sessions() as db:
        db.add(
            User(
                email="lifecycle-admin@example.com",
                full_name="Lifecycle Admin",
                password_hash=hash_password("StrongLifecycleAdminPassword123!"),
                role="admin",
                is_active=True,
            )
        )
        db.commit()

    def override_get_db():
        session = sessions()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, sessions

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def register(client: TestClient, email: str, **extra: object):
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Lifecycle Customer",
            "password": "StrongLifecycleCustomerPassword123!",
            **extra,
        },
    )


def login(client: TestClient, email: str, password: str):
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )


def test_public_registration_cannot_assign_privileged_role(auth_client):
    client, _ = auth_client

    response = register(client, "role-escalation@example.com", role="admin")

    assert response.status_code == 201, response.text
    assert response.json()["role"] == "customer"

    credentials = login(
        client,
        "role-escalation@example.com",
        "StrongLifecycleCustomerPassword123!",
    )
    assert credentials.status_code == 200
    headers = {"Authorization": f"Bearer {credentials.json()['access_token']}"}
    assert client.post(
        "/api/v1/scheduling/slots",
        headers=headers,
        json={
            "delivery_date": "2099-01-01",
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "capacity": 1,
        },
    ).status_code == 403


def test_deactivated_account_cannot_login_or_reuse_existing_token(auth_client):
    client, sessions = auth_client
    registered = register(client, "deactivated@example.com")
    assert registered.status_code == 201, registered.text

    credentials = login(
        client,
        "deactivated@example.com",
        "StrongLifecycleCustomerPassword123!",
    )
    assert credentials.status_code == 200
    token = credentials.json()["access_token"]

    with sessions() as db:
        user = db.query(User).filter_by(email="deactivated@example.com").one()
        user.is_active = False
        db.commit()

    rejected_login = login(
        client,
        "deactivated@example.com",
        "StrongLifecycleCustomerPassword123!",
    )
    assert rejected_login.status_code == 401
    assert rejected_login.json()["detail"] == "Incorrect email or password."

    rejected_request = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rejected_request.status_code == 401


def test_login_uses_same_public_error_for_unknown_email_and_wrong_password(auth_client):
    client, _ = auth_client
    register(client, "known-account@example.com")

    unknown = login(client, "missing-account@example.com", "AnyPassword123!")
    wrong_password = login(
        client,
        "known-account@example.com",
        "IncorrectPassword123!",
    )

    assert unknown.status_code == wrong_password.status_code == 401
    assert unknown.json()["detail"] == wrong_password.json()["detail"]
