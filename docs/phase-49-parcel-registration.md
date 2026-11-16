# Phase 49 — parcel registration reliability

## Changes
- Ignore stale PIN-code serviceability responses when the customer edits the PIN or starts a newer check.
- Invalidate pending checks immediately when the PIN changes and on component unmount.
- Keep coverage lookup errors distinct from a confirmed unsupported PIN code, with an explicit retry action.
- Sanitize PIN input to six numeric digits and announce coverage feedback accessibly.
- Recheck the exact PIN being submitted and stop parcel creation if the PIN changes during validation.
- Preserve the existing serviceability and parcel-creation API contracts.

## Acceptance checks
- A delayed response for an older PIN never replaces the latest coverage state.
- Editing the PIN clears stale success, failure, and lookup-error feedback.
- A network/API lookup failure is recoverable and is not presented as an unsupported service area.
- Parcel creation cannot proceed on an unverified or changed PIN.
- The existing parcel registration and scheduling flow remains unchanged for a confirmed serviceable PIN.
