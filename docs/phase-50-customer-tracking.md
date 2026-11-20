# Phase 50 — customer tracking freshness

## Changes
- Refresh the customer parcel list and delivery assignment/ETA data automatically every 60 seconds while the tracking page is open.
- Refresh immediately when the customer returns to the visible browser tab.
- Avoid overlapping requests and ignore responses invalidated by page cleanup.
- Keep existing parcel data visible during silent refreshes instead of replacing the page with loading skeletons.
- Show the last successful refresh time and a clear recovery action when refresh fails.
- Format ETA windows safely, including windows crossing midnight or dates; malformed or reversed timestamps never render as misleading dates.

## Acceptance checks
- Initial page load still shows the existing loading state.
- Periodic refresh does not overlap an in-flight parcel/tracking request.
- Background tabs do not continue polling.
- Returning to the page triggers a refresh.
- Failed refreshes preserve the last successful data and offer a retry.
- ETA formatting handles same-day, cross-day, invalid, and reversed windows.
- No backend or API contract changes are required.
