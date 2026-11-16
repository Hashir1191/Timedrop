# Phase 37 — Operations UI and responsive notification queue

## Notification queue workspace

The operations portal now includes a dedicated Notification queue page.

- Lists the latest 100 outbox deliveries using the admin-only operations API.
- Filters by delivery status and channel.
- Shows delivery ID, message subject, masked recipient, attempt count, timestamps, status, and the last provider error.
- Exposes a retry action only for failed jobs.
- Displays loading, empty, error, retry-in-progress, and success states.
- Uses the existing operations design language on desktop and switches to compact stacked cards on narrow screens.

Recipient contact details remain masked in the API response and UI. The page does not fabricate delivery metrics; summary counts are derived only from the records currently loaded.

## Accessibility and interaction

- Filters use explicit labels.
- Retry controls are disabled while a retry request is in progress.
- Errors and successful requeue confirmations use live status regions.
- The page supports keyboard operation and visible focus behavior inherited from the shared design system.

## Verification

The frontend production build runs in CI and checks TypeScript types before bundling. The operations API and retry behavior are covered by Phase 36 backend tests.
