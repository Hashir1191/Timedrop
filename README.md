# TimeDrop

TimeDrop is an India-first last-mile delivery scheduling platform prototype.

The pilot must only handle parcels that TimeDrop is explicitly authorized to receive and handle. Use synthetic data during development.

## Current milestone

- FastAPI application with Swagger/OpenAPI documentation
- SQLAlchemy + SQLite persistence for local development
- Customer registration and JWT login
- Separate role-based customer and operations web portals
- Customer parcel creation, personal parcel list, and delivery booking management
- Operations delivery-slot management and booking register
- Delivery partner accounts provisioned by operations admins
- Parcel assignment to active delivery partners (only after a delivery slot is booked)
- Partner-only assignment inbox and controlled delivery status transitions
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

Operations creates partner accounts; public registration always creates customers. Assignments require an active booking and an active, available partner. A partner can only see and update their own assignments. The allowed lifecycle is assigned → accepted → out_for_delivery → delivered, with failed as an allowed terminal outcome from assigned, accepted, or out_for_delivery. Failed updates require a reason in the request; the current prototype stores the status but does not yet persist a structured failure-reason or proof-of-delivery record.

## Run on Windows PowerShell

Create and activate a virtual environment:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements-dev.txt
```

Copy `.env.example` to `.env` and set a long, random `SECRET_KEY`. Do not commit `.env`.

Start the API:

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
- Configure HTTPS and restrict CORS before external use.
- Replace localStorage token storage with a production-grade session design before production.
- Replace the prototype SQLite compatibility approach with versioned Alembic migrations and PostgreSQL before production.
- Do not accept, store, transport, or deliver third-party marketplace parcels unless the relevant seller, carrier, and operational parties have explicitly authorized the arrangement.
