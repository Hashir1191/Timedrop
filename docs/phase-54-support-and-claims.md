# Phase 54 — Customer support and claims

## Customer portal

Customers can open a support case from the customer navigation and:
- Choose a category: missing parcel, suspected theft, damaged parcel, marked delivered but not received, app bug, or other.
- Link a parcel that belongs to their account.
- Describe what happened and receive a unique case reference.
- Review case status and support replies.
- Add follow-up messages while a case is open.

Suspected theft and missing-parcel cases are initially assigned high priority. This is a triage default, not an automated finding or liability decision.

## Operations inbox

Administrators can:
- Review the support queue and filter by status.
- Assign a case to an active operations administrator.
- Change priority and lifecycle status.
- Send customer-visible replies.
- Add internal notes that are never returned to customer endpoints.
- Reopen a case by changing its status; closing/resolving a case prevents further customer replies until a new case is opened.

## API and data integrity

- Customer routes are scoped to the authenticated customer.
- A linked parcel must belong to the case creator.
- Customer requests cannot create internal notes or change case status/priority/assignee.
- Admin assignment targets must be active administrator accounts.
- Every lifecycle change and message is stored in support case records; lifecycle changes also create append-only support case events.
- Customer-visible status changes and support replies create in-app notifications.
- Internal notes are excluded from customer list and detail responses.

## Current scope boundaries

This phase records a structured claim and supports a two-way conversation. Secure evidence uploads (photos, delivery-area images and documents), malware scanning, object-storage retention, and a formal claim investigation/decision workflow are separate work and must be implemented before treating this as a full theft/insurance claims process. Do not promise reimbursement or deduct partner earnings from a case record alone.

## Manual acceptance

1. Sign in as a customer and open Support centre.
2. Submit an app bug report and a missing-parcel report linked to a parcel.
3. Confirm each receives a unique case number and appears in the case list.
4. Sign in as operations and open Support inbox.
5. Assign a case to yourself, raise its priority and move it to in progress.
6. Add an internal note and verify it is visible to operations but absent from the customer's view.
7. Send a customer-visible reply and verify the customer receives an in-app notification.
8. Reply as the customer and confirm the case returns to in progress.
9. Resolve the case and confirm the customer cannot continue the closed conversation.
