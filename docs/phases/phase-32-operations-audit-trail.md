# Phase 32 — Operations audit trail

## Goal

Provide traceability for important administrative and operational configuration changes, without storing sensitive submitted values.

## Recorded events

- Delivery partner created, profile/capacity/availability updated.
- Service area created or updated.
- Blackout date created or updated.
- Delivery slot created or updated.

## API

`GET /api/v1/operations/audit-log?entity_type=&action=&from_date=&to_date=&skip=&limit=`

The endpoint is administrator-only and returns the actor name, action, entity reference, summary, changed field names, and timestamp. It supports entity/action/date filters and pagination (maximum 500 records per request).

## Privacy and integrity

- Audit entries record changed field names, not submitted values.
- Contact details, email addresses, passwords, and arbitrary request payloads are not copied into the audit log.
- The application exposes no update or delete endpoint for audit entries.
- Existing parcel custody and delivery-event timelines remain the detailed record for parcel movement; this audit log focuses on administrative configuration changes.

## Data

Adds `operations_audit_logs` through Alembic revision `20261115_0014`, following revision `20261115_0013`.

## UI

A dedicated operations Audit log page provides date and entity filters, actor attribution, timestamps, and changed-field tags.

## Validation

Backend tests cover recorded event types, filters, admin-only access, and exclusion of sensitive values. Local and end-to-end testing remain deferred.
