# Phase 44 — End-to-end product readiness

## Goal

Strengthen the application's pilot-readiness checks without requiring paid hosting or a public domain. This phase adds focused authentication lifecycle regression coverage to the existing backend and frontend build gates.

## Changes

- Add regression coverage proving public customer registration cannot assign an administrative role through an extra request field.
- Verify deactivating an account blocks both new logins and previously issued access tokens.
- Verify login failures do not reveal whether an email address is registered.
- Keep all test users and data synthetic and isolated in an in-memory SQLite database.
- Continue using the existing CI backend suite, frontend production build, PostgreSQL migration integration, Docker builds, and production Compose validation.

## Validation

The GitHub Actions CI workflow runs the new tests as part of the complete backend test suite. A successful run is required before merge.

## Scope and limitations

These tests improve regression coverage; they are not a penetration test, load test, or guarantee of production security. The existing end-to-end delivery journey remains covered separately. No live deployment, external provider integration, VPS, or domain is required for this phase.

## Local verification

From the repository root:

```powershell
$env:PYTHONPATH = "backend"
python -m pytest backend/tests/test_auth_lifecycle.py -v
python -m pytest backend/tests -v
```
