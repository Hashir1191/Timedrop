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
        cors_origins="https://app.example.com",
        trusted_hosts="app.example.com,127.0.0.1",
    )

    settings.validate_for_startup()


def test_notification_worker_settings_reject_invalid_retry_configuration():
    settings = Settings(
        notification_max_attempts=0,
        notification_retry_base_seconds=10,
        notification_retry_max_seconds=5,
    )

    with pytest.raises(RuntimeError, match="NOTIFICATION_MAX_ATTEMPTS"):
        settings.validate_for_startup()


def test_notification_worker_settings_accept_defaults():
    settings = Settings()

    settings.validate_for_startup()



def test_development_allowed_hosts_include_test_client_host():
    settings = Settings(app_env="development")

    assert "testserver" in settings.allowed_hosts


def test_production_rejects_missing_trusted_hosts():
    settings = Settings(
        app_env="production",
        secret_key="a" * 48,
        database_url="postgresql+psycopg://user:password@localhost/timedrop",
        cors_origins="https://app.example.com",
    )

    with pytest.raises(RuntimeError, match="TRUSTED_HOSTS"):
        settings.validate_for_startup()


def test_production_rejects_wildcard_or_non_https_cors():
    settings = Settings(
        app_env="production",
        secret_key="a" * 48,
        database_url="postgresql+psycopg://user:password@localhost/timedrop",
        cors_origins="http://app.example.com",
        trusted_hosts="app.example.com,127.0.0.1",
    )

    with pytest.raises(RuntimeError, match="HTTPS"):
        settings.validate_for_startup()


def test_production_accepts_explicit_https_origin_and_host():
    settings = Settings(
        app_env="production",
        secret_key="a" * 48,
        database_url="postgresql+psycopg://user:password@localhost/timedrop",
        cors_origins="https://app.example.com",
        trusted_hosts="app.example.com,127.0.0.1",
    )

    settings.validate_for_startup()


def test_allowed_hosts_are_parsed_and_whitespace_is_removed():
    settings = Settings(trusted_hosts=" app.example.com, 127.0.0.1 ,, ")

    assert settings.allowed_hosts == ["app.example.com", "127.0.0.1"]


def test_production_rejects_wildcard_trusted_hosts():
    settings = Settings(
        app_env="production",
        secret_key="a" * 48,
        database_url="postgresql+psycopg://user:password@localhost/timedrop",
        cors_origins="https://app.example.com",
        trusted_hosts="*,app.example.com",
    )

    with pytest.raises(RuntimeError, match="TRUSTED_HOSTS"):
        settings.validate_for_startup()


def test_production_rejects_wildcard_cors_origin():
    settings = Settings(
        app_env="production",
        secret_key="a" * 48,
        database_url="postgresql+psycopg://user:password@localhost/timedrop",
        cors_origins="*",
        trusted_hosts="app.example.com,127.0.0.1",
    )

    with pytest.raises(RuntimeError, match="HTTPS"):
        settings.validate_for_startup()
