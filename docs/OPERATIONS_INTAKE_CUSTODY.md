# Operations parcel intake and custody

## Purpose

Record the physical receipt of an authorized parcel into TimeDrop's operational custody and the later handover to the assigned delivery partner.

## Intake workflow

1. An operations administrator opens **Parcel intake**.
2. The administrator enters the parcel tracking number, recipient, destination, and recipient phone.
3. The administrator may link the parcel to an existing active customer account by email. The API does not create customer accounts.
4. The administrator records who handed over the parcel, its visible condition (intact, damaged, or opened), and optional intake notes.
5. The API creates the parcel and its first `received` custody event in one database transaction.
6. The intake record is visible in the operations list and its custody history can be reviewed.

## Handover workflow

1. The parcel must have a delivery slot and an assigned delivery partner.
2. Operations physically hands the parcel to that assigned partner.
3. Operations records the handover in **Parcel intake → View history → Record partner handover**.
4. The API appends a `released` event with the assigned partner's name and the operations actor/timestamp.
5. A second release is rejected.

## API

All endpoints require an authenticated operations administrator:

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/operations/intake` | Register parcel and record receipt |
| GET | `/api/v1/operations/intake` | List latest 100 intake records |
| GET | `/api/v1/operations/parcels/{parcel_id}/custody` | Read custody history |
| POST | `/api/v1/operations/parcels/{parcel_id}/release` | Record partner handover |

## Data and controls

- Tracking numbers remain globally unique.
- Optional customer linking accepts an existing active customer account only.
- Package condition is recorded as `intact`, `damaged`, or `opened`.
- Custody events are append-only at the application layer; an event is never updated in place.
- Release requires an assignment whose status is exactly `assigned`.
- The assigned partner's name is captured as the handover recipient.
- The migration adds `parcel_custody_events`; apply Alembic migrations before using this feature.

## Pilot limitations

This is not yet a tamper-proof audit ledger, barcode scanner integration, photo evidence workflow, multi-warehouse inventory system, or chain-of-custody signature capture. Use synthetic data during development and receive only parcels TimeDrop is explicitly authorized to handle.
