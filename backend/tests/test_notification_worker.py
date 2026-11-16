from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.config import settings
from app.notification_worker import _recover_stale_deliveries, _retry_delay_seconds


class FakeResult:
    def __init__(self, items):
        self.items = items

    def all(self):
        return self.items


class FakeSession:
    def __init__(self, items):
        self.items = items

    def scalars(self, statement):
        return FakeResult(self.items)


def test_retry_delay_uses_exponential_backoff_and_caps(monkeypatch):
    monkeypatch.setattr(settings, "notification_retry_base_seconds", 5)
    monkeypatch.setattr(settings, "notification_retry_max_seconds", 30)

    assert _retry_delay_seconds(1) == 5
    assert _retry_delay_seconds(2) == 10
    assert _retry_delay_seconds(3) == 20
    assert _retry_delay_seconds(4) == 30
    assert _retry_delay_seconds(10) == 30


def test_expired_worker_lease_is_requeued_and_counts_as_attempt(monkeypatch):
    now = datetime.now(timezone.utc)
    item = SimpleNamespace(
        attempts=1,
        status="processing",
        locked_at=now - timedelta(minutes=10),
        last_error=None,
        next_attempt_at=now,
    )
    monkeypatch.setattr(settings, "notification_delivery_lease_seconds", 60)
    monkeypatch.setattr(settings, "notification_max_attempts", 5)
    monkeypatch.setattr(settings, "notification_retry_base_seconds", 5)
    monkeypatch.setattr(settings, "notification_retry_max_seconds", 300)

    recovered = _recover_stale_deliveries(FakeSession([item]), now)

    assert recovered == 1
    assert item.status == "pending"
    assert item.attempts == 2
    assert item.locked_at is None
    assert item.last_error == "Worker lease expired before delivery was acknowledged."
    assert item.next_attempt_at == now + timedelta(seconds=10)


def test_expired_worker_lease_fails_when_retry_limit_is_reached(monkeypatch):
    now = datetime.now(timezone.utc)
    item = SimpleNamespace(
        attempts=4,
        status="processing",
        locked_at=now - timedelta(minutes=10),
        last_error=None,
        next_attempt_at=now,
    )
    monkeypatch.setattr(settings, "notification_delivery_lease_seconds", 60)
    monkeypatch.setattr(settings, "notification_max_attempts", 5)

    recovered = _recover_stale_deliveries(FakeSession([item]), now)

    assert recovered == 1
    assert item.status == "failed"
    assert item.attempts == 5
    assert item.locked_at is None
    assert item.last_error == "Worker lease expired before delivery was acknowledged."


def test_recovery_returns_zero_when_no_expired_leases_exist():
    now = datetime.now(timezone.utc)

    assert _recover_stale_deliveries(FakeSession([]), now) == 0
