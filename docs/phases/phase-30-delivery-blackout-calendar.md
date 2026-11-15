# Phase 30 — Delivery blackout calendar

## Goal

Let operations mark dates when TimeDrop cannot accept new delivery slots or bookings, without deleting slots or disturbing confirmed customer bookings.

## Capabilities

- Operations-only list, create, and activate/deactivate endpoints for blackout dates.
- A reason is required for each closure.
- Slot creation is blocked on active blackout dates.
- Customer slot availability returns no slots for a blackout date.
- Booking and rescheduling use the same backend closure check.
- Existing confirmed bookings prevent a date from being closed until operations reschedules or cancels them.
- Deactivating a blackout reopens previously created active slots.
- Operations UI provides a dedicated blackout calendar and the slot manager shows a closure notice.

## API

- `GET /api/v1/operations/blackout-dates?from_date=&to_date=&include_inactive=`
- `POST /api/v1/operations/blackout-dates`
- `PATCH /api/v1/operations/blackout-dates/{blackout_id}`

## Rules

- Only administrators can manage blackout records.
- Dates must be today or in the future when created or activated.
- One record exists per date; inactive records can be reactivated rather than duplicated.
- A closure cannot be activated while active bookings exist for the date.
- Existing slots remain stored. While a blackout is active they are hidden from customer availability and cannot be booked.
- No automatic cancellation, rescheduling, or notification is performed as part of closure creation.

## Data

Adds `delivery_blackout_dates` through Alembic revision `20261115_0013`, following revision `20261115_0012`.

## Validation

Backend tests cover closure creation, slot and booking enforcement, preservation of existing bookings, reopening dates, and admin-only controls. Local and end-to-end testing remain deferred.
