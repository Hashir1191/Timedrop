# Phase 41 — Production security hardening

## API host and origin validation

The API now applies Starlette TrustedHostMiddleware. Development defaults allow localhost, 127.0.0.1, and TestClient's testserver host. Production requires an explicit TRUSTED_HOSTS allowlist with at least one public hostname; wildcard hosts are rejected.

Production startup also requires CORS_ORIGINS to contain explicit HTTPS origins only. Empty or wildcard CORS configuration is rejected. Configure hostnames without a scheme or path, for example app.example.com,127.0.0.1. Include 127.0.0.1 because the container health check calls the API directly on loopback.

The production Compose file requires TRUSTED_HOSTS. Keep it synchronized with the public hostname accepted by the TLS reverse proxy.

## Browser security headers

Nginx now sends:
- Content-Security-Policy restricting scripts and connections to the same origin, while permitting HTTPS map tiles and inline styles required by the current UI.
- Strict-Transport-Security after the external HTTPS proxy is configured.
- Permissions-Policy disabling camera, microphone, and browser geolocation.
- X-Content-Type-Options, Referrer-Policy, and X-Frame-Options.

The policy keeps the current map tile use case working while preventing browser geolocation collection, which TimeDrop does not require. If future integrations need additional external script, image, font, or API hosts, update the CSP deliberately and test the exact feature.

## Deployment requirements

Example production values:

~~~dotenv
CORS_ORIGINS=https://app.example.com
TRUSTED_HOSTS=app.example.com,127.0.0.1
~~~

The TLS reverse proxy must terminate HTTPS and forward the original Host and X-Forwarded-Proto headers. Do not expose the Nginx HTTP port directly to the public internet. HSTS is meaningful only when the browser-facing endpoint is served over HTTPS.

## Verification

Tests cover allowed-host parsing, rejection of wildcard trusted hosts, rejection of wildcard/non-HTTPS production CORS, and HTTP requests with untrusted Host headers. CI builds the Nginx image and runs the complete backend suite.
