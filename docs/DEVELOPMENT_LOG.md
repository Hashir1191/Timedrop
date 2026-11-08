# TimeDrop Development Log

## Day 1 — Project foundation
- Created the FastAPI service, health endpoint, smoke tests, and MVP scope.

## Day 2 — Parcel management API
- Added SQLAlchemy Parcel model, Pydantic schemas, and parcel registration/list/retrieval/status endpoints.
- Confirmed two health-check smoke tests passed in the local development session.

## Day 3 — Delivery scheduling engine
- Added dated delivery slots with configurable capacity.
- Added availability lookup that reports remaining capacity.
- Added parcel booking, rescheduling, and cancellation.
- Used a conditional database update to reserve capacity only when a slot has space.
- Rescheduling reserves the new slot before releasing the old slot.
- Added tests for availability, overbooking, rescheduling, cancellation, and duplicate slot windows.

### Scheduling assumptions
- Slot dates and times use Asia/Kolkata (IST).
- Operations staff creates slot windows; automatic recurring slot generation is not part of this milestone.
- Capacity is a per-slot count, not yet constrained by delivery partner, route, vehicle, or geographic zone.

### Next milestone
Add authentication and authorization so only operations users can create slots, and customers can manage only their own parcel bookings. Add a proper database migration workflow before production deployment.
