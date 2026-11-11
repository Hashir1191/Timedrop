# TimeDrop

TimeDrop is an India-first last-mile delivery scheduling platform prototype.

The pilot must only handle parcels that TimeDrop is explicitly authorized to receive and handle. Use synthetic data during development.

## Current milestone

- FastAPI application with Swagger/OpenAPI documentation
- SQLAlchemy persistence with SQLite for local development and PostgreSQL support
- Alembic versioned database migrations, including a non-destructive baseline adoption migration for existing pilot databases
- Customer registration and JWT login
- Separate role-based customer and operations web portals
- Customer parcel creation, personal parcel list, and delivery booking management
- Operations delivery-slot management and booking register
- Delivery partner accounts provisioned by operations admins
- Parcel assignment to active delivery partners (only after a delivery slot is booked)
- Partner-only assignment inbox and controlled delivery status transitions
- Append-only delivery event history with actor, timestamps, status changes and failure notes
- One-time-code proof of delivery with 30-minute expiry, hashed storage and five-attempt lockout
- Argon2 password hashing and role-based access control

## Delivery partner API

All endpoints are under `/api/v1/delivery`.

| Method | Endpoint | Access |
|---|---|---|
| POST | `/partners` | Admin |
| GET | `/partners` | Admin |
| POST | `/parcels/{parcel_id}/assignments` | Admin |
| GET | `/assignments` | Admin |
| GET | `/my-assignments` | Delivery partner |
| PATCH | `/assignments/{assignment_id}/status` | Assigned delivery partner |
| GET | `/assignments/{assignment_id}/events` | Admin, assigned partner, or parcel owner |
| POST | `/parcels/{parcel_id}/delivery-code` | Parcel owner; only while out for delivery |
| POST | `/assignments/{assignment_id}/proof` | Assigned delivery partner |

Operations creates partner accounts; public registration always creates customers. Assignments require an active booking and an active, available partner. A partner can only see and update their own assignments. The allowed lifecycle is assigned → accepted → out_for_delivery → delivered, with failed as an allowed terminal outcome from assigned, accepted, or out_for_delivery. Failed updates require a reason, which is persisted on the assignment. Delivery events are written when operations assigns a parcel and when a partner changes delivery status. The operations and partner portals display the event timeline. This is an append-only application event history, not a tamper-proof audit log. For proof of delivery, the parcel owner generates a six-digit code while the parcel is out for delivery. The code expires after 30 minutes, is stored only as an Argon2 hash, and is invalidated after five incorrect attempts or successful verification. A partner must submit the code and recipient name to complete delivery; the server records the recipient and timestamp and writes a proof event. Code delivery is currently shown inside the authenticated customer portal; SMS/email delivery and photo/signature evidence are not included.

## Run on Windows PowerShell

Create and activate a virtual environment:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements-dev.txt
```

Copy `.env.example` to `.env`. Local development uses SQLite by default. The API also supports PostgreSQL through `DATABASE_URL`; for example, use `postgresql+psycopg://timedrop_user:your_password@localhost:5432/timedrop`. Set `APP_ENV=production`, a unique `SECRET_KEY` of at least 32 characters, and the production `CORS_ORIGINS` before deployment. Production mode rejects the development secret and SQLite. Never commit `.env`.

### Apply database migrations

Run this from the repository root after activating the virtual environment:

```powershell
$env:PYTHONPATH = "backend"
alembic -c backend\alembic.ini upgrade head
```

This command is required for a new database and after each future schema migration. The first migration creates missing tables and conditionally adds the ownership, delivery-failure, and proof-of-delivery fields introduced in earlier pilot versions. It is designed to preserve existing rows; it does not delete or recreate the database.

Check the current migration revision:

```powershell
alembic -c backend\alembic.ini current
```

Start the API only after migrations have completed:

```powershell
$env:PYTHONPATH = "backend"
python -m uvicorn app.main:app --reload --app-dir backend
```

Open Swagger UI at http://127.0.0.1:8000/docs.

Run tests:

```powershell
$env:PYTHONPATH = "backend"
python -m pytest backend\tests -v
```

## Frontend

The React + Vite + TypeScript frontend lives in `frontend/`.

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Keep the API running in a separate terminal.

## Security and operations

- Never commit `.env` or share passwords/access tokens.
- Configure HTTPS and set `CORS_ORIGINS` to only the trusted frontend origins before external use.
- Configure `DATABASE_URL` for PostgreSQL in deployed environments; SQLite remains the local-development default.
- The PostgreSQL driver and Alembic are installed from `backend/requirements.txt`.
- Apply database migrations as a deployment step before starting new application instances; the API intentionally does not mutate the schema at startup.
- Back up the database before applying migrations to any environment containing important data.
- Replace localStorage token storage with a production-grade session design before production.
- Do not accept, store, transport, or deliver third-party marketplace parcels unless the relevant seller, carrier, and operational parties have explicitly authorized the arrangement.
