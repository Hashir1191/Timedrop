# Phase 57 — Evidence-backed support cases

## Customer evidence

Customers can attach evidence to an open support case:
- PDF documents
- JPEG photos
- PNG images

Limits:
- 5 MB per file
- 5 files per case
- 15 MB total per case

The server checks the declared MIME type, filename extension and file signature (magic bytes), calculates a SHA-256 hash and records the uploader and server timestamp. Files are stored against the case and are not exposed through public file URLs.

## Privacy and access

- Customers can upload evidence only to their own support cases.
- Customer APIs return only customer-visible attachments.
- Internal operations attachments are excluded from customer case responses and customer download routes.
- Operations administrators can review all case evidence.
- Downloads require an authenticated customer owner or operations administrator and are forced as attachments with `nosniff` and private/no-store cache headers.
- Closed cases must be reopened before new evidence can be added.

## Security boundaries

File type checks and size limits reduce risk but do not replace malware scanning. The current implementation does not claim that uploaded files are virus-free. Before a public production rollout, add an antivirus/content-disarm pipeline, encrypted object storage, retention/deletion controls, audit alerts and per-account upload rate limits. Files are currently stored in PostgreSQL; a later storage architecture phase should move larger evidence blobs to controlled object storage.

## Manual acceptance

1. Open a customer support case.
2. Attach a PDF, JPEG or PNG under 5 MB.
3. Confirm it appears in the customer's case and the operations inbox.
4. Upload an internal operations file and confirm the customer cannot see or download it.
5. Try an unsupported file type and a MIME/extension mismatch; both must be rejected.
6. Confirm downloads require authentication and return a SHA-256 evidence header.
7. Confirm the per-case file count and total size limits are enforced.
