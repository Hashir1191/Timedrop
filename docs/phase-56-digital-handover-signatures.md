# Phase 56 — Signed delivery-partner handover

## Handover flow

1. Operations records the parcel's physical release to the assigned delivery partner.
2. The partner sees a handover acknowledgement in their assignment workspace.
3. The partner reviews the account name and acknowledgement statement, draws a signature using mouse, stylus or touchscreen, and explicitly checks the acknowledgement.
4. The server verifies the authenticated partner owns the assignment, the latest custody event is the matching release, and the typed signer name matches the partner account.
5. TimeDrop stores the PNG signature, SHA-256 hash, server timestamp, partner identity, parcel, assignment and exact custody-event reference.
6. The assignment response shows that the handover is signed. For assignments with a recorded release event, the partner cannot accept the assignment until the signature is recorded.

## Evidence and access

- Signature bytes are stored with the handover record and are not returned by normal assignment APIs.
- The API stores a SHA-256 hash for integrity checking and appends a `handover_signed` delivery event to the parcel timeline.
- Duplicate signatures for the same assignment are rejected.
- Signature publishing is partner-authenticated and assignment-owner scoped.
- The signature image is limited to PNG and 256 KB.
- The partner's typed signer name must match their authenticated account name.

## Acknowledgement statement

The partner confirms physical receipt of the identified parcel and acknowledgement of the recorded condition/handover record. The statement explicitly says later loss or damage is subject to TimeDrop's documented investigation and dispute process.

A signature proves that the authenticated partner account acknowledged the handover event. It does not independently establish negligence, conclusively prove the parcel's condition, or authorize automatic salary deductions. Any financial responsibility requires evidence, investigation, an opportunity to respond, and a lawful documented decision.

## Scope boundaries

This phase covers warehouse-to-partner acknowledgement. Recipient signatures at the final doorstep delivery, photo evidence, partner offline signing, trusted device attestation, PDF handover certificates and richer operations review screens are future enhancements.

## Manual acceptance

1. Operations receives a parcel, assigns it to a partner and records the physical release.
2. The partner refreshes their assignment list and sees the signature panel.
3. Try accepting before signing; the API must reject the transition.
4. Draw a signature, check the acknowledgement and submit.
5. Confirm the assignment shows a signed timestamp.
6. Accept the assignment successfully.
7. Confirm the customer parcel timeline shows the partner handover acknowledgement.
8. Attempt to sign a second time; the API must reject the duplicate.
