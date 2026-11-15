# Phase 29 — PIN-code serviceability management

## Goal

Allow TimeDrop operations to control which Indian PIN codes are currently supported and prevent customers from registering parcels for unsupported destinations.

## Capabilities

- Public serviceability lookup for a six-digit PIN code.
- Admin-only service-area list, create, and update endpoints.
- Active/inactive coverage states; records are deactivated rather than deleted.
- Customer parcel registration is enforced against active service-area records.
- Customer parcel form displays the result of a PIN-code lookup before submission.
- Operations service-area screen supports adding, searching, pausing, and reactivating PIN codes.

## API

- `GET /api/v1/serviceability/{pincode}`
- `GET /api/v1/operations/service-areas/?q=&include_inactive=`
- `POST /api/v1/operations/service-areas/`
- `PATCH /api/v1/operations/service-areas/{area_id}`

## Rules

- PIN codes must be six digits and cannot begin with zero.
- Duplicate PIN-code records are rejected.
- Unknown and inactive PIN codes are not serviceable.
- Customer parcel registration fails with HTTP 409 unless an active service-area record exists.
- Pausing a PIN code affects new registrations only. Existing parcels and deliveries are not cancelled or modified.
- No service areas are seeded automatically. Operations must explicitly configure its supported geography.

## Data

Adds `serviceable_pincodes` through Alembic revision `20261115_0012`, following revision `20261113_0011`.

## Validation

Backend tests cover public lookup, active/inactive coverage, parcel creation enforcement, duplicate records, invalid PIN codes, and admin-only management. Local and end-to-end testing remain deferred to the planned testing stage.
