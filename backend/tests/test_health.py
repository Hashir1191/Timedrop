from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import app
from app.routers import health

client = TestClient(app)


def test_health_check_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "timedrop-api",
    }


def test_readiness_check_confirms_database_connection() -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "timedrop-api",
        "checks": {"database": "ok"},
    }


def test_readiness_check_returns_service_unavailable_when_database_fails(monkeypatch) -> None:
    class UnavailableConnection:
        def __enter__(self):
            raise SQLAlchemyError("database unavailable")

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setattr(health.engine, "connect", lambda: UnavailableConnection())

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "service": "timedrop-api",
        "checks": {"database": "unavailable"},
    }


def test_root_returns_api_welcome_message() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == "Welcome to TimeDrop API"
