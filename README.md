# TimeDrop

TimeDrop is an India-first last-mile delivery scheduling platform prototype.

The pilot must only handle parcels that TimeDrop is explicitly authorized to receive and handle. Use synthetic data during development.

## Current milestone

- FastAPI application with Swagger/OpenAPI documentation
- SQLAlchemy persistence with SQLite for local development and PostgreSQL support
- Alembic versioned database migrations, including a non-destructive baseline adoption migration for existing pilot databases
- Docker Compose development environment with PostgreSQL 16 and a non-root FastAPI container
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

Copy `.env.example` to `.env`. Local non-Docker development uses SQLite by default. Set `APP_ENV=production`, a unique `SECRET_KEY` of at least 32 characters, and the production `CORS_ORIGINS` before deployment. Production mode rejects the development secret and SQLite. Never commit `.env`.

### Option A: Run with SQLite (existing local workflow)

Apply database migrations from the repository root:

```powershell
$env:PYTHONPATH = "backend"
python -m alembic -c backend\alembic.ini upgrade head
python -m alembic -c backend\alembic.ini current
```

The first migration creates missing tables and conditionally adds the ownership, delivery-failure, and proof-of-delivery fields introduced in earlier pilot versions. It is designed to preserve existing rows; it does not delete or recreate the database.

Start the API after migrations:

```powershell
$env:PYTHONPATH = "backend"
python -m uvicorn app.main:app --reload --app-dir backend
```

Open Swagger UI at http://127.0.0.1:8000/docs.

### Option B: Run the API and PostgreSQL with Docker Compose

Install and start Docker Desktop, then run these commands from the repository root:

```powershell
docker compose config
docker compose up --build -d
docker compose ps
docker compose logs -f api
```

Compose starts PostgreSQL 16 with a persistent named volume, waits for its health check, builds the API image, applies Alembic migrations, and then starts FastAPI. The API is available at http://localhost:8000 and Swagger UI at http://localhost:8000/docs. PostgreSQL is exposed on localhost:5432 for database tools. The frontend can continue running locally with the steps in the Frontend section.

For the local Compose environment, the defaults are intentionally development-only. Override `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `SECRET_KEY`, and ports through the root `.env` file before sharing the environment or exposing it beyond your machine. Use a URL-safe PostgreSQL password; if it contains reserved URL characters, percent-encode it when constructing a connection URL.

Stop containers while retaining the database volume:

```powershell
docker compose down
```

Stop containers and permanently delete the Compose database volume (destructive; only for disposable local data):

```powershell
docker compose down -v
```

**SQLite data is not copied into the Compose PostgreSQL database.** The two databases are separate. Keep using SQLite for your existing pilot data until the dedicated SQLite-to-PostgreSQL export/import utility has been implemented and verified. Do not run `docker compose down -v` if you need to preserve PostgreSQL data.

Run tests after the development phase is complete:

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

Open http://localhost:5173. Keep the API running in a separate terminal. For the Docker Compose backend, the frontend still runs locally and calls the API at localhost:8000.

## Security and operations

- Never commit `.env` or share passwords/access tokens.
- Configure HTTPS and set `CORS_ORIGINS` to only the trusted frontend origins before external use.
- Configure `DATABASE_URL` for PostgreSQL in deployed environments; SQLite remains the local non-Docker development default.
- The PostgreSQL driver and Alembic are installed from `backend/requirements.txt`.
- Apply database migrations as a deployment step before starting new application instances; the API intentionally does not mutate the schema at startup. The Compose command applies migrations for this single-instance local development setup.
- Back up the database before applying migrations to any environment containing important data.
- Replace localStorage token storage with a production-grade session design before production.
- Do not accept, store, transport, or deliver third-party marketplace parcels unless the relevant seller, carrier, and operational parties have explicitly authorized the arrangement.
