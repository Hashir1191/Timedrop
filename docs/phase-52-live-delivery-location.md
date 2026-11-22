# Phase 52 — Live delivery location foundation

## Outcome

TimeDrop can accept a delivery partner's GPS position during an active out-for-delivery assignment and expose only the latest position to the parcel's verified owner. This is the backend foundation for the customer live map and partner location-sharing controls.

## API

- `POST /api/v1/delivery/assignments/{assignment_id}/location`
  - Delivery-partner authentication required.
  - The authenticated partner must own the assignment.
  - The assignment must be `out_for_delivery`.
  - Latitude and longitude are range-validated; optional accuracy is limited to 1,000 metres.
  - Updates sent less than five seconds apart are rejected with HTTP 429.
  - The server timestamps the ping; client clocks are not trusted.

- `GET /api/v1/delivery/parcels/{parcel_id}/live-location`
  - Customer authentication required.
  - The parcel must belong to the signed-in customer.
  - The assignment must be `out_for_delivery`.
  - Returns only the latest coordinate, accuracy, server timestamp and existing ETA window; it does not expose the partner's account, phone number or location history.
  - A position is marked live only when it is no more than 120 seconds old. Older positions are explicitly marked stale.
  - Before the first GPS ping, the response reports `awaiting_location` without coordinates.

## Privacy and operational controls

- Location publishing is restricted to the assigned partner and only during the active delivery leg.
- Customers cannot query another customer's parcel location; unauthorized parcel lookups return 404.
- Location updates are not exposed as a customer-readable trail. The customer endpoint returns the latest position only.
- The backend enforces a minimum five-second update interval. A production mobile client should normally send updates every 15–30 seconds while actively navigating, subject to OS background-location permission and battery policy.
- Location collection must stop when the assignment leaves `out_for_delivery`; the endpoint rejects further updates.
- The customer map must show the age of the last position and never imply that a stale coordinate is live.
- A production rollout still needs a documented retention/deletion schedule, location-consent UX, and platform-specific background-location permission review.

## What this phase does not claim

This phase does not yet provide a rendered customer map, continuous background GPS capture, traffic-aware recalculated ETA, geofencing, turn-by-turn navigation, or a live production map provider. The existing published ETA window remains the source of the customer's arrival estimate. The next UI phase will consume this API and add a partner-side location-sharing control.

## Verification

Regression coverage verifies:
- Location cannot be published before the assignment reaches `out_for_delivery`.
- Valid GPS updates can be published and read by the parcel owner.
- Another customer cannot read the parcel's location.
- Invalid coordinates are rejected.
- Rapid repeat updates are throttled.
