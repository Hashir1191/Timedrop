# TimeDrop

TimeDrop is an India-first last-mile delivery scheduling platform prototype.

The pilot must only handle parcels that TimeDrop is explicitly authorized to receive and handle. Use synthetic data during development.

## Current milestone

- FastAPI application with Swagger/OpenAPI documentation
- SQLAlchemy + SQLite persistence for local development
- Customer registration and JWT login
- Separate role-based customer and operations web portals
- Customer parcel creation, personal parcel list, and delivery booking management
- Argon2 password hashing
- Customer/admin role-based access control
- Parcel ownership checks
- Delivery-slot creation and availability lookup
- Capacity-aware parcel booking with overbooking protection
- Parcel rescheduling and booking cancellation
- Admin booking register with parcel and delivery-slot details, status/date filters, and cancelled-booking history
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
| GET | `/api/v1/scheduling/parcels/{parcel_id}/bookings` | Owner or admin |
| POST | `/api/v1/scheduling/parcels/{parcel_id}/bookings` | Owner or admin |
| PATCH | `/api/v1/scheduling/parcels/{parcel_id}/bookings` | Owner or admin |
| DELETE | `/api/v1/scheduling/parcels/{parcel_id}/bookings` | Owner or admin |
| GET | `/api/v1/scheduling/bookings` | Admin |

Login returns a bearer access token. In Swagger UI, click **Authorize** and enter the token using the Bearer authentication scheme.

All delivery dates and slot times are interpreted as India Standard Time (Asia/Kolkata).

### Admin booking register

`GET /api/v1/scheduling/bookings` is restricted to operations admins. It returns booking records joined with the associated parcel and delivery slot, including recipient/tracking details, delivery address summary, reserved date/time, slot capacity, booking status, and timestamps. Optional query parameters are `status=booked|cancelled`, `delivery_date=YYYY-MM-DD`, `skip`, and `limit` (maximum 500). Omitting `status` returns both active and cancelled booking records. The frontend defaults to active bookings and lets operations view cancelled records or all records. The current data model keeps one booking row per parcel, so booking a previously cancelled parcel reactivates that row rather than creating a separate historical event.

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

## Run the frontend operations dashboard

The frontend is a React + Vite + TypeScript application in `frontend/`. It provides role-based sign-in and separate customer and operations portals. Customers can register, create parcels, view their own parcel list, inspect delivery-slot availability, book a slot, reschedule, and cancel. Operations admins retain the overview, parcel search/status updates, delivery-slot creation/availability, and detailed booking register. The customer portal uses owner-protected API endpoints and cannot access operations-only pages.

In a **new PowerShell terminal** from the repository root:

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Open http://localhost:5173. Keep the FastAPI server running separately at http://127.0.0.1:8000. Open the sign-in page. Customers can create an account from the registration link; operations administrators sign in with their provisioned credentials. The app routes each role to its own portal. The frontend uses the API base URL from `frontend/.env`; change `VITE_API_BASE_URL` if your backend runs elsewhere.

Before sharing the dashboard outside local development, configure HTTPS, restrict allowed frontend origins in the backend CORS policy, and move beyond browser localStorage token storage to a production-grade session design.

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

## Verify the customer parcel workflow in Swagger

Use synthetic recipient details only. Start the API, open http://127.0.0.1:8000/docs, and follow this sequence:

1. Register a customer with `POST /api/v1/auth/register`.
2. Log in as that customer with `POST /api/v1/auth/login`; copy the returned `access_token`.
3. Click **Authorize** in Swagger and provide the bearer token. Protected GET and POST requests will otherwise return `401`.
4. Create a parcel with `POST /api/v1/parcels/` using a payload like:

```json
{
  "tracking_number": "TD-DEMO-001",
  "recipient_name": "Synthetic Recipient",
  "phone": "9876543210",
  "address_line": "12 Example Test Street",
  "city": "Prayagraj",
  "state": "Uttar Pradesh",
  "pincode": "211001",
  "delivery_instructions": "Synthetic test parcel only"
}
```

5. Call `GET /api/v1/parcels/` and `GET /api/v1/parcels/{parcel_id}` while authorized as the customer. The customer should see only parcels they own.
6. Log in as an operations admin, replace the Swagger authorization with the admin token, and call `GET /api/v1/parcels/` again. The admin should see all parcels.
7. A second customer should receive `404` when requesting another customer's parcel by ID; this intentionally avoids revealing whether another user's parcel exists.

The automated test `test_customer_parcel_create_list_and_admin_visibility_workflow` covers customer registration, login, parcel creation, customer listing/detail retrieval, and admin visibility.

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
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── api.ts
│   │   ├── auth.ts
│   │   └── main.tsx
│   ├── .env.example
│   └── package.json
├── .env.example
└── README.md
```

## Product and operational boundary

Do not accept, store, transport, or deliver third-party marketplace parcels unless the relevant seller, carrier, and operational parties have explicitly authorized the arrangement.
