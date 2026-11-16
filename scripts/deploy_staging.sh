#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.production.yml}"
ENV_FILE="${ENV_FILE:-.env.staging}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RELEASE_VERSION="${RELEASE_VERSION:?Set RELEASE_VERSION, for example 0.9.0}"
APP_BASE_URL="${APP_BASE_URL:?Set APP_BASE_URL to the public staging HTTPS URL}"
BACKUP_AGE_RECIPIENT="${BACKUP_AGE_RECIPIENT:?Set BACKUP_AGE_RECIPIENT to the age public recipient}"

if [[ ! "$RELEASE_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][A-Za-z0-9.-]+)?$ ]]; then
  echo "RELEASE_VERSION must be a semantic version without the leading v (for example 0.9.0)." >&2
  exit 1
fi
if [[ "$APP_BASE_URL" != https://* ]]; then
  echo "APP_BASE_URL must use HTTPS." >&2
  exit 1
fi
[[ -f "$COMPOSE_FILE" ]] || { echo "Compose file not found: $COMPOSE_FILE" >&2; exit 1; }
[[ -f "$ENV_FILE" ]] || { echo "Staging environment file not found: $ENV_FILE" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "docker is required." >&2; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "curl is required." >&2; exit 1; }
command -v age >/dev/null 2>&1 || { echo "age is required for the pre-deployment backup." >&2; exit 1; }

export TIMEDROP_API_IMAGE="ghcr.io/hashir1191/timedrop-api:$RELEASE_VERSION"
export TIMEDROP_WEB_IMAGE="ghcr.io/hashir1191/timedrop-web:$RELEASE_VERSION"

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

echo "Validating staging Compose configuration..."
compose config --quiet

echo "Starting PostgreSQL before taking the pre-deployment backup..."
compose up -d db
compose exec -T db sh -c 'until pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"; do sleep 2; done'

echo "Creating encrypted pre-deployment database backup..."
COMPOSE_FILE="$COMPOSE_FILE" ENV_FILE="$ENV_FILE" BACKUP_DIR="$BACKUP_DIR" \
  BACKUP_AGE_RECIPIENT="$BACKUP_AGE_RECIPIENT" bash scripts/backup_postgres.sh

echo "Pulling immutable release images: $RELEASE_VERSION"
compose pull api web notification-worker

echo "Applying release. The API container applies Alembic migrations before serving traffic..."
compose up -d api web notification-worker

echo "Waiting for the public readiness endpoint..."
ready=0
for attempt in $(seq 1 "${DEPLOY_HEALTH_ATTEMPTS:-30}"); do
  if curl --fail --silent --show-error --max-time 10 "$APP_BASE_URL/health/ready" >/dev/null; then
    ready=1
    break
  fi
  sleep "${DEPLOY_HEALTH_INTERVAL_SECONDS:-10}"
done
if [[ "$ready" != 1 ]]; then
  echo "Deployment did not become ready. Do not delete the backup; inspect Compose logs and follow the rollback runbook." >&2
  compose ps
  exit 1
fi

echo "Running public release smoke tests..."
APP_BASE_URL="$APP_BASE_URL" bash scripts/smoke_test_release.sh

echo "Staging deployment verified for release $RELEASE_VERSION."
compose ps
