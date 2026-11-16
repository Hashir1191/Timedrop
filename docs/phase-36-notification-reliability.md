# Phase 36 — Notification delivery reliability

## Worker lease recovery

The outbox worker now uses a configurable delivery lease. A delivery left in processing beyond NOTIFICATION_DELIVERY_LEASE_SECONDS is considered abandoned. Recovery locks expired rows with SKIP LOCKED so concurrent workers do not count the same expired lease twice.

Each expired lease increments the delivery attempt count. The job is returned to pending with a retry time, or moved to failed when NOTIFICATION_MAX_ATTEMPTS is reached. A generic lease-expired reason is stored rather than an exception or provider response.

## Retry policy

Retries use capped exponential backoff:

- NOTIFICATION_RETRY_BASE_SECONDS: initial delay (default 5 seconds).
- NOTIFICATION_RETRY_MAX_SECONDS: maximum delay (default 300 seconds).
- NOTIFICATION_MAX_ATTEMPTS: maximum attempts before terminal failure (default 5).
- NOTIFICATION_DELIVERY_LEASE_SECONDS: processing lease before crash recovery (default 300 seconds).
- NOTIFICATION_WORKER_POLL_SECONDS: idle polling interval (default 5 seconds).

The worker validates these settings on startup and fails fast for invalid values.

## Delivery guarantees

The outbox provides durable, at-least-once dispatch attempts, not universal exactly-once delivery. Email requests carry the stable outbox idempotency key in the Resend Idempotency-Key header. The MSG91 Flow adapter does not currently send a provider-supported idempotency token. If MSG91 accepts an SMS but the worker loses the response or crashes before persisting success, a later retry may submit the SMS again. Operations should account for this when reviewing provider delivery logs.

The worker continues to re-check account activation, phone verification, and SMS consent immediately before dispatch. A withdrawn consent or inactive account cancels a queued SMS job before provider submission.

## Operations API

Administrators can inspect the latest outbox records using GET /api/v1/operations/notification-deliveries with optional status, channel, skip, and limit filters. Recipient values are masked in the response. The endpoint is admin-only.

A failed delivery can be manually requeued with POST /api/v1/operations/notification-deliveries/{id}/retry. Only failed records can be requeued; the action is written to the append-only operations audit log. The original attempt count is retained. The worker re-checks SMS verification and consent before any retry is submitted.

## Operational review

Inspect failed and currently processing jobs without selecting recipient contact details:

~~~sql
SELECT id, channel, status, attempts, created_at, next_attempt_at, sent_at, last_error
FROM notification_deliveries
WHERE status IN ('failed', 'processing')
ORDER BY created_at DESC
LIMIT 100;
~~~

Monitor failed-job counts and worker logs. A processing row older than the configured lease should be recovered automatically on the next worker claim cycle. Investigate repeated failures at the provider and configuration level before manually re-enqueuing work.

## Verification

The new worker tests cover capped exponential backoff, recovery of abandoned leases, retry exhaustion, and the no-stale-work case. Run:

~~~powershell
$env:PYTHONPATH = "backend"
python -m pytest backend\tests\test_notification_worker.py backend\tests\test_config.py -v
~~~

No database schema migration is required.
