# Phase 50 — Customer delivery experience

## What changed
- Added a customer-facing delivery progress tracker to each parcel card, showing registration, scheduling, partner assignment, out-for-delivery, and completion.
- Added distinct terminal states for failed and cancelled deliveries.
- Made ETA presentation clearer and included the assignment's last-updated timestamp when available.
- Kept the ETA sourced from the existing customer-owned `GET /delivery/my-tracking` response; no new endpoint or authorization surface was introduced.
- Hardened parcel-list refreshes against overlapping requests and stale responses so an older request cannot overwrite newer data.
- Improved filter accessibility with `aria-pressed`, and made refresh/loading/error feedback clearer.
- Added responsive styling for narrow screens.

## Verification
The existing API contract is reused. GitHub Actions is the merge gate for backend tests, migration integration, Docker builds, workflow validation, frontend production build, and production Compose configuration.
