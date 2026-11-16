# Phase 43 — Staging deployment foundation

## What this phase provides

- A repeatable deployment script for a Linux staging host with Docker Engine and the Docker Compose plugin.
- A staging environment template that is intentionally not populated with real secrets.
- A pre-deployment encrypted PostgreSQL backup before application images are updated.
- Immutable API and web image selection by semantic release version.
- Readiness polling and the Phase 42 public HTTPS smoke test after deployment.

This phase does not create a cloud account, VM, DNS record, firewall rule, TLS certificate, registry credential, or public staging environment. It does not run a deployment from GitHub because no authorized staging host or SSH credentials have been supplied.

## Staging host prerequisites

Use a dedicated Linux VM (Ubuntu LTS is a practical default) with:

- A supported Docker Engine and Docker Compose plugin.
- A domain such as `staging.example.com` pointing to the VM.
- Inbound TCP 80 and 443 available to the TLS reverse proxy, plus SSH restricted to trusted administrator IPs.
- An external TLS reverse proxy in front of the TimeDrop web container. The current production Compose file exposes the web container on `WEB_PORT` (default 8080); do not expose that port publicly. The proxy must forward the original Host and X-Forwarded-Proto headers and terminate HTTPS.
- Enough persistent disk for PostgreSQL data and encrypted backups. Configure off-host backup storage before relying on the VM as a recovery target.

The database is on a private Compose network. Do not publish PostgreSQL port 5432 to the public internet.

## Prepare the staging environment

1. Clone the repository on the staging host and check out the approved release commit.
2. Copy `.env.staging.example` to `.env.staging`.
3. Replace all placeholders. Generate a unique `SECRET_KEY` of at least 32 characters and a long URL-safe alphanumeric PostgreSQL password. Set `CORS_ORIGINS` to the exact HTTPS origin and `TRUSTED_HOSTS` to the public hostname plus `127.0.0.1`.
4. Set file permissions: `chmod 600 .env.staging`.
5. Install `age` and create an age key pair. Keep the private identity outside the VM or in a separately secured secret store; place only the public recipient in the deployment environment as `BACKUP_AGE_RECIPIENT`.
6. Authenticate Docker to GHCR with a read-only package token that can pull the TimeDrop API and web packages. Do not use a personal account password.
7. Configure the external HTTPS reverse proxy and verify its certificate before deploying.

## Deploy a release

Run from the repository root on the staging host:

```bash
RELEASE_VERSION=0.9.0 \
APP_BASE_URL=https://staging.example.com \
BACKUP_AGE_RECIPIENT=age1... \
ENV_FILE=.env.staging \
bash scripts/deploy_staging.sh
```

The script validates Compose configuration, starts PostgreSQL, creates an encrypted backup, pulls the version-pinned API/web images, updates the API/web/worker services, waits for public API readiness, and runs the Phase 42 smoke checks. It fails closed if required tools, configuration, HTTPS, backup encryption, readiness, or smoke checks are missing.

The API image applies Alembic migrations before starting the web server. The deployment script deliberately does not run a destructive database downgrade or automatic rollback. If the release fails after a migration, preserve the backup and logs, inspect migration compatibility, and follow the operator-approved recovery plan.

## Release image publishing

The existing `.github/workflows/release-images.yml` publishes versioned GHCR images when a `vX.Y.Z` tag is pushed. After the publish workflow succeeds, deploy the corresponding version without the leading `v` (for example tag `v0.9.0` maps to image version `0.9.0`). Confirm the package visibility and pull permissions before attempting staging deployment.

## Post-deployment acceptance

- Confirm all Compose services are healthy with `docker compose --env-file .env.staging -f docker-compose.production.yml ps`.
- Run the HTTPS smoke test (the deployment script does this automatically).
- Sign in with staging-only customer, delivery-partner, and operations accounts; verify the end-to-end workflow using synthetic data.
- Confirm the notification worker heartbeat and queue in System Health.
- Perform a restore drill into a separate database using the Phase 42 restore procedure.
- Keep the release tag, image digests, migration revision, backup checksum, smoke output, and restore result in the release record.

## Security and cost controls

- Do not commit `.env.staging`, age private keys, registry tokens, provider credentials, or customer data.
- Keep SSH restricted, use a dedicated deploy account, and grant only the permissions required to run Docker Compose.
- Keep database backups encrypted and copy them off-host; local VM backups alone do not protect against VM/disk loss.
- Do not enable SMS/email sending or route geocoding until provider credentials, consent, templates, quotas, and data handling are reviewed.
- Use a small staging VM initially, but do not choose a provider or incur hosting costs without explicit approval.

## Remaining external dependency

A real deployment requires the chosen VM/domain, TLS reverse proxy, GHCR pull credentials, age backup recipient, and staging secrets. None are fabricated or embedded in this repository. Once those are provisioned, the deployment script can be run by an authorized operator.
