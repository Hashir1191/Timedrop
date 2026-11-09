# TimeDrop

TimeDrop is an India-first last-mile delivery scheduling platform prototype.

The pilot must only handle parcels that TimeDrop is explicitly authorized to receive and handle. Use synthetic data during development.

## Current milestone

- FastAPI application with Swagger/OpenAPI documentation
- SQLAlchemy + SQLite persistence for local development
- Customer registration and JWT login
- Argon2 password hashing
- Customer/admin role-based access control
- Parcel ownership checks
- Delivery-slot creation and availability lookup
- Capacity-aware parcel booking with overbooking protection
- Parcel rescheduling and booking cancellation
- Pytest coverage for authentication, authorization, and scheduling

## Roles and permissions

| Capability | Customer | Operations admin |
|---|---:|---:|
| Register and log in | Yes | Provisioned separately |
| View own profile | Yes | Yes |
| Create parcels | Yes | Yes |
| List/view parcels | Own parcels only | All parcels |
| Create delivery slots | No | Yes |
| View slot availability | Yes | Yes |
| Book/reschedule/cancel own parcel | Yes | Yes |
| Update parcel status | No | Yes |

Public registration always creates a `customer`. A customer cannot assign themselves the `admin` role.

## API endpoints

| Method | Endpoint | Access |
|---|---|---|
| POST | `/api/v1/auth/register` | Public |
| POST | `/api/v1/auth/login` | Public |
| GET | `/api/v1/auth/me` | Authenticated |
| POST | `/api/v1/parcels/` | Authenticated |
| GET | `/api/v1/parcels/` | Authenticated |
| GET | `/api/v1/parcels/{parcel_id}` | Owner or admin |
| PATCH | `/api/v1/parcels/{parcel_id}/status` | Admin |
| POST | `/api/v1/scheduling/slots` | Admin |
| GET | `/api/v1/scheduling/slots?delivery_date=YYYY-MM-DD` | Authenticated |
| POST | `/api/v1/scheduling/parcels/{parcel_id}/bookings` | Owner or admin |
| PATCH | `/api/v1/scheduling/parcels/{parcel_id}/bookings` | Owner or admin |
| DELETE | `/api/v1/scheduling/parcels/{parcel_id}/bookings` | Owner or admin |

Login returns a bearer access token. In Swagger UI, click **Authorize** and enter the token using the Bearer authentication scheme.

All delivery dates and slot times are interpreted as India Standard Time (Asia/Kolkata).

## Scheduling rules

- Operations creates dated slots with a fixed capacity.
- Availability returns all active slots, including full slots with zero remaining capacity.
- A parcel can have one active booking at a time.
- Booking reserves capacity using a conditional database update, preventing capacity from exceeding the configured limit.
- Rescheduling reserves the destination slot before releasing the current slot.
- Cancellation releases one unit of capacity and returns the parcel to `registered`.
- Past delivery dates cannot be created or booked.

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

## Create the first operations administrator

In a separate PowerShell terminal, from the repository root:

```powershell
$env:PYTHONPATH = "backend"
$env:TIMEDROP_ADMIN_EMAIL = "ops@example.com"
$env:TIMEDROP_ADMIN_NAME = "TimeDrop Operations"
$env:TIMEDROP_ADMIN_PASSWORD = "Use-a-unique-password-at-least-12-chars"
python -m app.create_admin
```

Use your own email and a unique password. The script refuses to create an administrator if an account with that email already exists. Clear the temporary environment variables after provisioning:

```powershell
Remove-Item Env:TIMEDROP_ADMIN_EMAIL
Remove-Item Env:TIMEDROP_ADMIN_NAME
Remove-Item Env:TIMEDROP_ADMIN_PASSWORD
```

## Secure an existing admin account

If an admin password or access token has been exposed, pull the latest code and run this from the repository root with the API server stopped:

```powershell
$env:PYTHONPATH = "backend"
python -m app.secure_admin
```

The command interactively asks for the email of an existing active admin and a new password (the password is not echoed). It then:

- Replaces that admin's password hash using Argon2.
- Deactivates the known placeholder account `your-email@example.com`, if it exists.
- Rotates the `SECRET_KEY` entry in the local `.env` file, removing duplicate entries.
- Invalidates previously issued JWT access tokens. Restart the API server after the command completes.

Run this command only from the repository root, where the correct local `.env` and `timedrop.db` are located. It does not print passwords, password hashes, or the new secret. Keep `.env` private and never commit it.

## Run tests

```powershell
$env:PYTHONPATH = "backend"
python -m pytest backend\tests -v
```

## Database note

The local SQLite startup compatibility migration adds the nullable `owner_id` column to an existing parcels table. Existing parcels remain unowned and are visible only to administrators; they are not automatically assigned to a customer. This lightweight compatibility step is for the prototype. Before production, replace it with versioned Alembic migrations and PostgreSQL.

## Project structure

```text
timedrop/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── parcels.py
│   │   │   └── scheduling.py
│   │   ├── create_admin.py
│   │   ├── secure_admin.py
│   │   ├── migrations.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── security.py
│   │   └── main.py
│   └── tests/
│       ├── test_auth.py
│       ├── test_health.py
│       └── test_scheduling.py
├── .env.example
└── README.md
```

## Product and operational boundary

Do not accept, store, transport, or deliver third-party marketplace parcels unless the relevant seller, carrier, and operational parties have explicitly authorized the arrangement.
