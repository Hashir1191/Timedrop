# TimeDrop

TimeDrop is an India-first last-mile delivery scheduling platform prototype.

The first milestone is a local development environment with a FastAPI backend.
The initial pilot uses only parcels that TimeDrop is explicitly authorized to receive and handle.

## Current milestone

- FastAPI application with Swagger/OpenAPI documentation
- Health-check endpoint
- SQLAlchemy + SQLite persistence for local development
- Parcel registration, listing, retrieval, and status updates
- Pydantic request/response validation
- Pytest smoke tests

The current API supports these parcel endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/parcels/` | Register a parcel |
| `GET` | `/api/v1/parcels/` | List parcels (`skip` / `limit` pagination) |
| `GET` | `/api/v1/parcels/{parcel_id}` | Retrieve one parcel |
| `PATCH` | `/api/v1/parcels/{parcel_id}/status` | Update parcel status |

## Requirements

- Python 3.11 or newer
- Git
- VS Code

## Run on Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
uvicorn app.main:app --reload --app-dir backend
```

If PowerShell blocks activation, run this once in the current terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Open:
- API: http://127.0.0.1:8000
- Swagger docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

## Run tests

```powershell
pip install -r backend\requirements-dev.txt
$env:PYTHONPATH = "backend"
pytest
```

## Project structure

```text
timedrop/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── routers/
│   │       ├── __init__.py
│   │       └── parcels.py
│   ├── tests/
│   │   └── test_health.py
│   ├── .env.example
│   ├── requirements.txt
│   └── requirements-dev.txt
├── docs/
│   ├── MVP_SCOPE.md
│   └── DEVELOPMENT_LOG.md
├── .gitignore
└── README.md
```

## Product and operational boundary

Do not accept, store, transport, or deliver third-party marketplace parcels unless the relevant seller, carrier, and operational parties have explicitly authorized the arrangement. Use synthetic data during development.
