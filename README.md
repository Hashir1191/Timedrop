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

**SQLite data is not copied automatically into PostgreSQL.** The two databases are separate. Keep using SQLite for your existing pilot data until you are ready to perform a planned migration. Do not run `docker compose down -v` if you need to preserve PostgreSQL data.

#### Optional: transfer existing SQLite data to PostgreSQL

This is a deliberate, separate operation. First stop the API and any process that can write to SQLite, and make a backup:

```powershell
Copy-Item .\timedrop.db .\timedrop-before-postgres-migration.db
```

Start the Compose database and API so the PostgreSQL schema is created:

```powershell
docker compose up --build -d
docker compose ps
```

Run a read-only preflight (replace the example password with the value in your local `.env`):

```powershell
$env:PYTHONPATH = "backend"
python backend\scripts\migrate_sqlite_to_postgres.py --source .\timedrop.db --target-url "postgresql+psycopg://timedrop_user:change-this-local-docker-password@localhost:5432/timedrop"
```

The preflight checks that both databases have the same Alembic revision, the same business tables and columns, and that every PostgreSQL business table is empty. It prints the source row counts and changes no data.

Only after reviewing a successful preflight, repeat the command with `--execute`:

```powershell
python backend\scripts\migrate_sqlite_to_postgres.py --source .\timedrop.db --target-url "postgresql+psycopg://timedrop_user:change-this-local-docker-password@localhost:5432/timedrop" --execute
```

The utility reads SQLite in read-only mode, copies rows in foreign-key dependency order, preserves primary keys, updates PostgreSQL integer sequences, and writes all copied rows in one PostgreSQL transaction. It refuses to overwrite a non-empty target or proceed when schema/revision checks fail. Keep the SQLite backup until you have separately verified the PostgreSQL data and application behavior. Use a URL-safe password in the connection URL; percent-encode reserved URL characters.

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


## In-app notifications

TimeDrop stores user-scoped in-app notifications for key booking and delivery events. The inbox is available to customers, delivery partners, and operations users in the application header.

Current notification events include:
- Booking created, rescheduled, and cancelled (parcel owner).
- Delivery partner assigned (parcel owner and assigned partner).
- Assignment accepted, parcel out for delivery, and delivery failed (parcel owner).
- Delivery completed after proof-of-delivery verification (parcel owner).

Authenticated API endpoints:
- `GET /api/v1/notifications/` — list the signed-in user's latest notifications; supports `unread_only=true` and `limit`.
- `GET /api/v1/notifications/unread-count` — get the user's unread count.
- `PATCH /api/v1/notifications/{id}/read` — mark one of the signed-in user's notifications as read.
- `POST /api/v1/notifications/read-all` — mark all of the signed-in user's notifications as read.

Notification records are created in the same database transaction as the booking or delivery change. This prevents a notification from being stored when its underlying operation rolls back. The current implementation is in-app only; email and SMS delivery require a separately configured provider and are not yet enabled.


### Transactional email delivery

In-app notifications can also be delivered by the standalone email outbox worker. Configure `RESEND_API_KEY` and `NOTIFICATION_FROM_EMAIL` in your local `.env` file (never commit secrets), then start the stack with `docker compose up --build -d`. The API writes email jobs to `notification_deliveries` in the same transaction as the in-app notification. The separate worker sends pending jobs through Resend, uses an idempotency key, retries transient failures with backoff, and marks exhausted jobs as failed. Configure a verified sending domain/address in Resend before production use.

SMS provider settings are reserved for MSG91, but SMS dispatch is deliberately not enabled yet. Customer parcel phone numbers and admin-entered partner phone numbers are not verified or consented contact points in the current data model. Do not send delivery notifications to those numbers until TimeDrop adds an explicit phone-verification and SMS-consent flow and the required Indian DLT entity/header/template setup is completed. MSG91 requires an approved Flow/template; see the [MSG91 Send SMS API](https://docs.msg91.com/sms/send-sms) and [DLT template setup](https://msg91.com/help/template/how-to-create-flow-id-to-send-sms-via-api).


## Phone verification and SMS consent

Customer and delivery-partner accounts can manage a mobile number at **Phone & SMS** in their portal. The API normalizes Indian mobile numbers to +91 E.164 format, prevents a number from being linked to multiple accounts, invalidates older challenges when a new code is requested, stores only an Argon2 hash, expires codes after five minutes, limits verification to five attempts, and rate-limits requests to three per account per 15 minutes.

Endpoints (authenticated):
- `GET /api/v1/phone-verification/me` — current phone verification and SMS consent state.
- `POST /api/v1/phone-verification/request` — request a verification challenge.
- `POST /api/v1/phone-verification/verify` — verify a six-digit code.
- `PUT /api/v1/phone-verification/sms-consent` — explicitly enable or withdraw SMS notification consent.

**Development mode:** no SMS is sent. With `PHONE_OTP_EXPOSE_IN_DEVELOPMENT=true`, the API returns a development-only OTP in its response so the workflow can be exercised locally. Keep this setting disabled outside local development. Production mode rejects OTP requests until a real SMS provider is configured; the API never claims that an SMS was sent when no provider is active.

**SMS delivery remains disabled.** Verification and consent are separate. No message should be sent until the MSG91 Flow integration, approved Indian DLT entity/header/template details, and operational consent controls are configured. Existing delivery-partner phone fields remain unchanged; users verify the contact number on their own account profile.
