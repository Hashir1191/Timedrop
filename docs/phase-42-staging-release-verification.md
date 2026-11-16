# Phase 42 — Staging deployment and release verification

## Goal

Provide a repeatable, read-only verification step for a deployed release. This phase adds a public HTTPS smoke test and a release runbook. It does not deploy to a server, create cloud infrastructure, or claim that a live environment has passed.

## Automated smoke test

Run from the repository root after the release is deployed behind the HTTPS reverse proxy:

```bash
APP_BASE_URL=https://staging.example.com bash scripts/smoke_test_release.sh
```

The script checks:

- The frontend returns HTTP 200.
- Browser security headers are present on the frontend response.
- The reverse-proxied `/health/ready` endpoint returns HTTP 200 and reports both API readiness and database connectivity.
- The operations system-health endpoint rejects anonymous access with HTTP 401 or 403.

The script is intentionally read-only. It does not register accounts, create parcels, schedule deliveries, send OTPs, or trigger customer notifications. Do not disable TLS verification to make a deployment pass; fix the certificate or proxy configuration instead.

## Staging release checklist

Complete these steps in a non-production environment first:

1. Pin API and web images to the same immutable release tag; avoid deploying `latest` in a controlled release.
2. Confirm the production Compose configuration renders successfully with the staging environment file:
   `docker compose --env-file .env.staging -f docker-compose.production.yml config --quiet`.
3. Confirm the PostgreSQL service is healthy and the API, web, and notification-worker containers are running and healthy:
   `docker compose --env-file .env.staging -f docker-compose.production.yml ps`.
4. Before migration, take an encrypted PostgreSQL backup using `scripts/backup_postgres.sh`. Store the age private identity separately from the backup and keep the checksum.
5. Apply migrations using the release's documented deployment procedure. Confirm the Alembic revision is current using the migration tooling included with the API release image.
6. Run `APP_BASE_URL=https://staging.example.com bash scripts/smoke_test_release.sh`.
7. Sign in with dedicated staging customer, partner, and operations test accounts. Verify a complete parcel-to-delivery journey, including booking, assignment, partner status transitions, proof-of-delivery, customer timeline, and role isolation. Use synthetic data and staging-only contact details.
8. Verify the notification worker heartbeat and queue from the operations System Health page. Check logs for repeated errors, retry storms, failed migrations, and unexpected 5xx responses.
9. Perform a restore drill into a separate, isolated database using `scripts/restore_postgres_backup.sh`. Never point a restore drill at the active application database. Confirm the restored Alembic revision and table counts.
10. Record the release tag, image digests, migration revision, smoke-test output, backup artifact/checksum, restore result, and outstanding issues before approving production.

## Rollback and data safety

- Keep the previous known-good API and web image tags available.
- Application rollback does not automatically reverse database migrations. Review migration compatibility before rolling back application images.
- Do not run destructive downgrade commands as an emergency default.
- If a migration is not backward-compatible, use the documented recovery plan and a verified backup; involve the database owner before any production restore.
- A successful backup command is not proof of recoverability. A restore drill is required to demonstrate that the backup can be decrypted and restored.

## Production gate

Do not declare a release production-ready until the staging checklist is complete, critical/high-severity defects are resolved, a restore drill succeeds, and an authorized operator has reviewed the deployment. This repository change alone does not deploy TimeDrop or provision a public domain, TLS certificate, hosting account, SMS/email provider, or production credentials.

## Known operational boundaries

The public smoke test verifies the frontend, API/database readiness, selected security headers, and anonymous access control. It does not replace authenticated end-to-end workflow tests, load testing, penetration testing, monitoring/alerting setup, legal/compliance review, or operational authorization from delivery partners and carriers.
