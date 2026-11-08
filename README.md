# TimeDrop

TimeDrop is an India-first last-mile delivery scheduling platform prototype.

The first milestone is a local development environment with a FastAPI backend.
The initial pilot uses only parcels that TimeDrop is explicitly authorized to receive and handle.

## Current milestone

- FastAPI application with Swagger/OpenAPI documentation
- SQLAlchemy + SQLite persistence for local development
- Parcel registration, listing, retrieval, and status updates
- Delivery-slot creation and availability lookup
- Capacity-aware parcel booking with overbooking protection
- Parcel rescheduling and booking cancellation
- Pydantic request/response validation and pytest coverage

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/parcels/` | Register a parcel |
| GET | `/api/v1/parcels/` | List parcels |
| GET | `/api/v1/parcels/{parcel_id}` | Retrieve a parcel |
| PATCH | `/api/v1/parcels/{parcel_id}/status` | Update parcel status |
| POST | `/api/v1/scheduling/slots` | Create a delivery slot (operations) |
| GET | `/api/v1/scheduling/slots?delivery_date=YYYY-MM-DD` | View remaining capacity |
| POST | `/api/v1/scheduling/parcels/{parcel_id}/bookings` | Book a parcel |
| PATCH | `/api/v1/scheduling/parcels/{parcel_id}/bookings` | Reschedule a booking |
| DELETE | `/api/v1/scheduling/parcels/{parcel_id}/bookings` | Cancel a booking |

All delivery dates and slot times are interpreted as India Standard Time (Asia/Kolkata).

## Scheduling rules

- Operations creates dated slots with a fixed capacity.
- Availability only returns active slots with remaining capacity.
- A parcel can have one active booking at a time.
- Booking reserves capacity using a conditional database update, preventing capacity from exceeding the configured limit.
- Rescheduling reserves the destination slot before releasing the current slot.
- Cancellation releases one unit of capacity and returns the parcel to `registered`.
- Past delivery dates cannot be created or booked.

## Run on Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements-dev.txt
$env:PYTHONPATH = "backend"
uvicorn app.main:app --reload --app-dir backend
```

Open Swagger UI at http://127.0.0.1:8000/docs.

## Run tests

```powershell
$env:PYTHONPATH = "backend"
pytest
```

## Project structure

```text
timedrop/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── parcels.py
│   │   │   └── scheduling.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── main.py
│   └── tests/
│       ├── test_health.py
│       └── test_scheduling.py
├── docs/
├── .gitignore
└── README.md
```

## Product and operational boundary

Do not accept, store, transport, or deliver third-party marketplace parcels unless the relevant seller, carrier, and operational parties have explicitly authorized the arrangement. Use synthetic data during development.
