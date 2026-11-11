import pytest

from app.config import Settings


def test_allowed_origins_are_parsed_and_whitespace_is_removed():
    settings = Settings(cors_origins=" https://app.example.com, http://localhost:5173 ,, ")

    assert settings.allowed_origins == [
        "https://app.example.com",
        "http://localhost:5173",
    ]


def test_production_rejects_default_or_short_secret():
    settings = Settings(
        app_env="production",
        secret_key="too-short",
        database_url="postgresql+psycopg://user:password@localhost/timedrop",
    )

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        settings.validate_for_startup()


def test_production_rejects_sqlite():
    settings = Settings(
        app_env="production",
        secret_key="a" * 48,
        database_url="sqlite:///./timedrop.db",
    )

    with pytest.raises(RuntimeError, match="PostgreSQL"):
        settings.validate_for_startup()


def test_production_accepts_postgresql_and_long_secret():
    settings = Settings(
        app_env="production",
        secret_key="a" * 48,
        database_url="postgresql+psycopg://user:password@localhost/timedrop",
    )

    settings.validate_for_startup()
