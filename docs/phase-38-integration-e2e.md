# Phase 38 — Integration and end-to-end verification

## Cross-role delivery journey

A new API-level integration test exercises the main customer-to-delivery-partner journey in one isolated database:

1. Operations creates a customer serviceable area fixture and the customer registers/logs in.
2. The customer registers a parcel and books an available delivery slot.
3. Operations provisions a delivery partner and assigns the booked parcel.
4. The partner sees the assignment, accepts it, and marks it out for delivery.
5. The customer requests a one-time delivery code.
6. The partner submits the code and recipient name to complete proof of delivery.
7. The test verifies the customer's parcel timeline, delivery event history, in-app notifications, unread count, and read-all behavior.
8. A separate access-control scenario verifies that another customer cannot read the parcel timeline.

All test records use synthetic identities, addresses, phone numbers, and tracking references. The tests use an isolated in-memory SQLite database and do not contact email or SMS providers.

## PostgreSQL migration integration

CI now starts a PostgreSQL 16 service and applies the complete Alembic migration chain to a fresh database. The job then reports the current migration revision. This complements the API tests and production Compose configuration validation by checking migrations against the production database engine.

## CI coverage

The CI pipeline now includes:

- Complete backend pytest suite, including the cross-role journey.
- Frontend TypeScript check and production Vite build.
- Production Docker Compose configuration validation.
- Backup/restore shell syntax validation.
- Fresh PostgreSQL 16 migration upgrade and revision verification.

## Local verification

Run the journey test:

~~~powershell
$env:PYTHONPATH = "backend"
python -m pytest backend\tests\test_end_to_end_delivery_journey.py -v
~~~

Run all backend tests:

~~~powershell
$env:PYTHONPATH = "backend"
python -m pytest backend\tests -v
~~~

The PostgreSQL migration job is run in GitHub Actions with a disposable PostgreSQL 16 service. It does not connect to or modify a deployment database.
