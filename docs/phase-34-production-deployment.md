# Phase 34 — Production deployment architecture

## Overview

This phase adds a production-oriented Docker Compose topology without changing the existing local development workflow.

- **web** builds the React/Vite frontend into static assets and serves them with Nginx.
- **api** runs FastAPI and applies Alembic migrations at startup.
- **notification-worker** runs the durable notification outbox worker separately from web requests.
- **db** runs PostgreSQL 16 on a private data network.
- Nginx serves the SPA, proxies /api/ to FastAPI, and proxies the readiness endpoint. The browser uses the same origin and does not need a public API port.

The database is not published to the host. Only the web service publishes a port. The API and database are not directly exposed to the public network by this Compose file.

## Requirements before deployment

1. A Linux host with Docker Engine and the Docker Compose plugin.
2. A domain name and HTTPS termination. Put a trusted TLS reverse proxy/load balancer in front of the published web port; do not expose plain HTTP directly to the public internet.
3. A deployment secret store or a protected .env file with restrictive permissions.
4. A unique SECRET_KEY with at least 32 characters.
5. Strong PostgreSQL credentials. Use URL-safe characters in POSTGRES_PASSWORD; percent-encode reserved characters if you choose to use them.
6. An exact public HTTPS origin in CORS_ORIGINS, e.g. https://app.example.com.
7. A monitored contact in ROUTE_PROVIDER_USER_AGENT, even when map routing is disabled.

Do not commit production .env files, passwords, API keys, or customer data.

## Configure and start

Create a deployment .env beside docker-compose.production.yml. Set the published image tags and the following values:

~~~dotenv
POSTGRES_DB=timedrop
POSTGRES_USER=timedrop_app
POSTGRES_PASSWORD=replace-with-a-long-url-safe-random-password
SECRET_KEY=replace-with-a-unique-random-secret-of-at-least-32-characters
CORS_ORIGINS=https://app.example.com
TRUSTED_HOSTS=app.example.com,127.0.0.1
NOTIFICATION_FROM_EMAIL=TimeDrop <notifications@example.com>
ROUTE_PROVIDER_USER_AGENT=TimeDrop/1.0 (production; contact: ops@example.com)
WEB_PORT=8080
TIMEDROP_API_IMAGE=ghcr.io/hashir1191/timedrop-api:1.0.0
TIMEDROP_WEB_IMAGE=ghcr.io/hashir1191/timedrop-web:1.0.0
~~~

Add provider credentials only when the corresponding email/SMS feature has been approved and configured. Keep SMS disabled until the MSG91 Flow template and Indian DLT requirements are satisfied. Production phone OTP exposure is forced off by the Compose configuration.

Validate interpolation and service configuration before starting:

~~~bash
docker compose --env-file .env -f docker-compose.production.yml config
docker compose --env-file .env -f docker-compose.production.yml pull
docker compose --env-file .env -f docker-compose.production.yml up -d
docker compose --env-file .env -f docker-compose.production.yml ps
docker compose --env-file .env -f docker-compose.production.yml logs -f api
~~~

Authenticate the deployment host to GitHub Container Registry before pulling private packages. The release workflow publishes immutable semantic-version tags and a latest tag; pin an explicit version in production rather than relying on latest. The public application is served on the configured WEB_PORT. Configure the TLS proxy to forward to that port and preserve the original host and forwarded protocol headers.

## Deployment and migration behavior

The API image applies Alembic migrations before starting Uvicorn. Keep this topology at one API replica during this phase. Before every deployment:

- take and verify a database backup;
- review pending migration revisions;
- deploy during a controlled maintenance window when a migration may lock or rewrite large tables;
- confirm API readiness and run the release smoke checks.

Do not scale API replicas horizontally while each container startup runs migrations. A later release pipeline should separate one migration job from application replicas before scaling.

## Persistence and recovery cautions

PostgreSQL data is stored in the named Docker volume timedrop_production_postgres_data. A Docker volume is persistent storage, not a backup. Configure off-host encrypted backups and test restores before accepting real operational data. Never use docker compose down -v on a deployment that contains data you need.

## Operational checks

- API readiness: /health/ready (proxied through Nginx).
- API liveness: /health (internal to the API service).
- Review container health with docker compose ps.
- Review logs for API and notification worker errors; do not log secrets or OTP values.
- Confirm the external TLS proxy enforces HTTPS and that the public origin is the only allowed CORS origin.

## Scope and limitations

This is a single-host production deployment baseline, not a highly available architecture. It does not provision DNS, TLS certificates, cloud infrastructure, managed PostgreSQL, object storage, centralized secrets, log aggregation, or automated off-site backups. Those require environment-specific infrastructure decisions. Do not use the public Nominatim/OSRM demo endpoints as production routing infrastructure; use a compliant hosted provider or self-hosted service when routing is enabled.
