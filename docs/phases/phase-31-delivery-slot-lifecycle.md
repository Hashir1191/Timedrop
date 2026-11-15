# Phase 31 — Delivery slot lifecycle and capacity management

## Goal

Give operations direct control over delivery slot capacity and activation after a slot has been created, while protecting confirmed bookings.

## API

- `PATCH /api/v1/scheduling/slots/{slot_id}`
- `GET /api/v1/scheduling/slots?delivery_date=YYYY-MM-DD&include_inactive=true` (admin-only option)

## Rules

- Slot capacity must remain between 1 and 500.
- Capacity cannot be reduced below the slot's confirmed booking count.
- A slot with confirmed bookings cannot be paused until those bookings are moved or cancelled.
- Paused slots are excluded from customer availability.
- Only administrators can request inactive slots or update a slot.
- Reactivation is rejected for past dates and active blackout dates.
- Updating a slot does not cancel, move, or alter existing bookings.

## UI

The operations delivery-slot screen includes capacity editing, pause/reactivate actions, and clear paused/closed-date states. The existing blackout calendar remains authoritative for date-wide closures.

## Data

No migration is required; the phase uses the existing `delivery_slots.capacity` and `delivery_slots.is_active` fields.

## Validation

Backend tests cover capacity changes, booked-slot protection, blackout-aware reactivation, and admin-only access. Local and end-to-end testing remain deferred.
