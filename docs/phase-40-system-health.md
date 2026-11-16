# Phase 40 — Worker heartbeat and system health monitoring

## Worker heartbeat

The notification worker now upserts a named heartbeat record on every processing loop, including idle loops. The heartbeat is stored in the same database as the notification outbox. PostgreSQL and SQLite use native conflict-safe upserts so multiple worker instances update one shared worker record rather than creating duplicate rows.

The worker heartbeat is separate from job lease state:
- A heartbeat indicates that the worker loop can reach and write to the database.
- A delivery lease indicates that a particular notification job is currently claimed.
- A healthy heartbeat does not prove that Resend or MSG91 is reachable or that a message reached its destination.

## Operations health API

Admin-only endpoint: GET /api/v1/operations/system-health

The response includes:
- Database status based on a successful request query.
- Notification worker state: healthy, stale, or not_seen.
- Last heartbeat timestamp and age.
- The configured freshness threshold.
- Counts of all notification outbox records grouped by status.
- Health-check timestamp.

A heartbeat is considered stale after max(30 seconds, three worker poll intervals plus 15 seconds). If the worker has never written a heartbeat, the status is not_seen.

## Operations UI

The admin navigation includes **System health**. The page shows database connectivity, worker heartbeat freshness, queue totals, and an actionable warning when the worker is stale or has not reported in. It supports manual refresh and responsive layouts.

The queue totals are database-wide counts, not the latest 100 rows displayed in the Notification queue page.

## Database migration

Alembic revision 20261116_0015 adds worker_heartbeats for existing pilot databases. It checks whether the baseline adoption migration has already created the table and index, preserving clean-database idempotency.

## Verification

Tests cover heartbeat upsert behavior, healthy/stale/missing worker states, queue counts, and admin-only access. PostgreSQL 16 CI applies the complete migration chain and repeats upgrade head to verify idempotency.

~~~powershell
$env:PYTHONPATH = "backend"
python -m pytest backend\tests\test_system_health.py -v
~~~
