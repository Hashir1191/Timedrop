# Phase 47 — parcel tracking activity experience

## Changes
- Give the parcel activity timeline explicit loading, error, and empty states.
- Allow customers to retry a failed timeline request and refresh activity without collapsing the parcel card.
- Guard against state updates after the timeline component unmounts or its parcel changes.
- Format timestamps safely and expose semantic time elements for assistive technology.
- Keep the existing timeline API and event ordering unchanged.

## Acceptance checks
- Opening activity displays a loading state while the timeline request is pending.
- A failed request displays a retry action; retry requests the same parcel timeline again.
- Empty history is distinct from loading and failure.
- Successful history shows update count, event title, readable timestamp, and description.
- Switching parcel cards during a pending request cannot write stale results into the next timeline.
