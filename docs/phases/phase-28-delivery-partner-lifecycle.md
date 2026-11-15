# Phase 28 — Delivery partner lifecycle management

## Goal

Give operations administrators safe controls over partner profile details, assignment capacity, assignment availability, and account activation without interrupting deliveries already in progress.

## API

`PATCH /api/v1/delivery/partners/{partner_id}` is admin-only and accepts a sparse JSON update containing any combination of:

- `full_name`
- `phone`
- `vehicle_type`
- `max_active_assignments` (1–50)
- `is_available`
- `is_active`

The response uses the existing delivery partner response shape, including current active assignment count and availability settings.

## Safety rules

- Pausing availability prevents new manual assignments and route-plan recommendations but does not cancel or alter active deliveries.
- Capacity cannot be reduced below the number of active assignments already in progress.
- Account deactivation is rejected while assignments are in `assigned`, `accepted`, or `out_for_delivery`.
- Deactivation also pauses new assignment availability.
- Reactivation does not automatically make the partner available; operations explicitly resumes new assignments after review.
- An inactive partner cannot be marked available.
- Empty updates, null field values, blank profile text, and out-of-range capacities are rejected.
- Customers and delivery partners cannot update partner accounts.

## Operations UI

The delivery-team register includes inline capacity editing, pause/resume controls, and guarded deactivate/reactivate actions. Deactivation is visibly disabled while active jobs remain.

## Data and migration

No database migration is required. The phase reuses the existing partner and user activation fields.

## Validation

Backend tests cover admin updates, role restrictions, invalid updates, pausing availability, and protection against deactivation while deliveries are active. GitHub Actions remains the CI validation source; local and end-to-end testing are deferred to the planned test stage.
