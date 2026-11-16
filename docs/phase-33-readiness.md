# Phase 33 — Database-aware readiness and container health

## Purpose

Separate process liveness from application readiness. A running FastAPI process is not ready to serve delivery workflows when its configured database cannot accept a query.

## Endpoints

- `GET /health` remains the lightweight liveness endpoint. It confirms that the API process is responding and does not depend on the database.
- `GET /health/ready` executes a lightweight `SELECT 1` using the configured SQLAlchemy engine. It returns HTTP 200 with a database check when successful, or HTTP 503 with a generic unavailable status when the database cannot be reached.

The readiness response intentionally excludes connection strings, exception messages, credentials, hostnames, and other infrastructure details.

## Container behavior

The backend Docker image now probes `/health/ready`. Docker therefore marks the API container unhealthy when the process is running but the database connection is unavailable. The existing Compose PostgreSQL health check and startup dependency remain in place.

## Verification

The health test suite covers the existing liveness contract, successful database readiness, and database failure behavior. Run:

```powershell
$env:PYTHONPATH = "backend"
python -m pytest backend\tests\test_health.py -v
```

This phase does not change business APIs, database schema, or customer data.
