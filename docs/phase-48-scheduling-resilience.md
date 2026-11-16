# Phase 48 — delivery scheduling resilience

## Changes
- Ignore stale parcel and slot responses when users navigate between parcels or dates.
- Separate slot-loading failures from empty availability so a service error is never presented as "no slots".
- Add a retry action for delivery-slot lookup failures.
- Prevent booking submission while slot data is loading or unavailable.
- Refresh slot availability after booking, rescheduling, and cancellation without issuing competing requests.

## Acceptance checks
- Rapidly changing the selected date never lets an older response overwrite the latest date.
- Failed slot or blackout-status lookups show a retry action.
- A slot request failure cannot be mistaken for a date with no availability.
- Booking and cancellation still use the existing API endpoints and refresh availability after success.
