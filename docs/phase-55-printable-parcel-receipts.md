# Phase 55 — Printable parcel registration receipts

## Issuance

A PDF registration receipt is generated inside the same database transaction whenever:
- A signed-in user registers a parcel through the customer parcel API.
- Operations registers a parcel through the warehouse intake workflow.

The receipt is stored with its parcel record, document number, verification code, SHA-256 hash, issuer account and issue timestamp. If PDF generation fails, the parcel registration transaction does not commit without its required receipt.

## Receipt contents

- TimeDrop branding and "Parcel Registration Receipt" document title.
- Tracking number and unique document number.
- Registration timestamp and registration status.
- Recipient and delivery destination.
- Masked contact phone number.
- Unique verification code and issuing service.
- Clear statement that registration is not proof of physical warehouse receipt, partner handover or final delivery.

## Access and verification

- Parcel receipt download is available only to the parcel owner or an operations administrator.
- The PDF is served as `application/pdf` and can be printed from a browser or PDF reader.
- The public verification endpoint accepts the high-entropy verification code and returns document validity, document number, tracking number, issue time and SHA-256 hash only. It does not disclose recipient address or contact details.
- The customer parcel workspace and operations parcel management screen include a receipt download action.

## Current scope boundaries

This phase delivers parcel registration receipts. Booking confirmations, partner handover slips, signature certificates, delivery proof documents and claim evidence packs will be added as their underlying workflows are implemented. A registration receipt is not a custody or delivery certificate.

The current implementation stores the PDF bytes in PostgreSQL. A future production storage phase should evaluate encrypted object storage, retention controls and archival/export policy as document volume grows.

## Manual acceptance

1. Register a parcel from the customer portal.
2. Open My parcels and download the registration receipt.
3. Print or save the PDF and check the tracking/document numbers, destination, masked phone and verification code.
4. Open the verification endpoint using the code and confirm the tracking number and SHA-256 match.
5. Register a parcel from Operations → Parcel intake and download its receipt from Parcel management.
6. Attempt to download another customer's receipt and confirm access is denied.
