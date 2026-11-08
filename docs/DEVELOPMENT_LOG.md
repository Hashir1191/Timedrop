# TimeDrop Development Log

## Day 1 — Project foundation

### Goal
Create a reproducible local backend environment and define the pilot scope.

### Deliverables
- Initial FastAPI service.
- Health-check endpoint.
- Automated smoke tests.
- MVP scope and operational boundaries.

### Validation
Run the backend locally and verify `/health` returns `{"status":"ok","service":"timedrop-api"}`.
Run `pytest` and confirm both tests pass.

### Next session
Define parcel lifecycle states and implement the first parcel data model and API contract.

## Day 2 — Parcel management API

### Deliverables
- SQLAlchemy `Parcel` model backed by SQLite for local development.
- Pydantic schemas for parcel creation, response serialization, and status updates.
- Parcel endpoints for registration, paginated listing, retrieval, and status changes.
- Duplicate tracking-number handling with HTTP 409.
- Package marker for the parcel router.

### Validation
The local development session reported two passing pytest smoke tests.
The parcel endpoints are documented in Swager UI at `/docs`.

### Next session
Add automated tests for parcel CRUD and validation, then design delivery-slot availability and booking rules.
