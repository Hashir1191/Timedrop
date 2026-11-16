# Phase 50 — parcel data validation and normalization

## Changes
- Normalize whitespace in tracking references, recipient names, street addresses, cities, and states before persistence.
- Reject whitespace-only required text values instead of accepting them as meaningful data.
- Validate contact numbers using a permissive international format while requiring 10–15 digits.
- Normalize optional delivery instructions and convert whitespace-only instructions to null.
- Keep parcel response fields and existing API routes unchanged.

## Acceptance checks
- Well-formed values with extra whitespace are stored in a consistent normalized form.
- Blank recipient/address/location values are rejected by request validation.
- Phone values with common formatting characters are accepted when they contain 10–15 digits.
- Alphabetic or too-short phone values are rejected with HTTP 422.
- Existing serviceability and parcel creation behavior remains covered by the regression suite.
