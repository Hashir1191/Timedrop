# Phase 45 — Frontend API resilience and session lifecycle

## Changes

- Centralize frontend HTTP handling for authenticated and public API requests.
- Convert network failures into a clear, actionable connection message rather than exposing browser-specific fetch errors.
- Handle non-JSON error responses and FastAPI validation-detail arrays safely.
- Treat unreadable successful JSON responses as a controlled API error.
- Broadcast a session-expired event when an authenticated API call returns HTTP 401. The application clears the stored token and returns the user to the public landing flow instead of leaving a stale authenticated interface visible.
- Keep 403 authorization failures distinct: they do not log the user out.
- Preserve the existing same-origin production API path and local development fallback.

## Validation

The frontend TypeScript production build is part of CI. Existing backend journey, role-access, and authentication lifecycle tests continue to run unchanged.

## Manual acceptance matrix

1. Sign in, then invalidate the token; the next authenticated API call clears the session.
2. Trigger a 403 as a customer; the account remains signed in and the permission error is shown.
3. Disconnect the API/network; the UI receives a clear connection error.
4. Return a non-JSON 500 response; the UI shows a stable fallback message.
5. Return a successful 204 response; mutation calls resolve without attempting JSON parsing.

No live infrastructure, third-party provider, or production credentials are needed.
