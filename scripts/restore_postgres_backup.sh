#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.production.yml}"
ENV_FILE="${ENV_FILE:-.env}"

: "${BACKUP_FILE:?Set BACKUP_FILE to an encrypted .dump.age backup}"
: "${AGE_IDENTITY:?Set AGE_IDENTITY to the path of the private age identity file}"
: "${RESTORE_DATABASE:?Set RESTORE_DATABASE to a NEW, separate database name}"

if [[ "${CONFIRM_RESTORE:-}" != "YES" ]]; then
  echo "Set CONFIRM_RESTORE=YES to confirm creation of a separate restore-test database." >&2
  exit 1
fi

command -v docker >/dev/null 2>&1 || { echo "docker is required." >&2; exit 1; }
command -v age >/dev/null 2>&1 || { echo "age is required." >&2; exit 1; }
command -v sha256sum >/dev/null 2>&1 || { echo "sha256sum is required." >&2; exit 1; }
[[ -f "$ENV_FILE" ]] || { echo "Environment file not found: $ENV_FILE" >&2; exit 1; }
[[ -f "$COMPOSE_FILE" ]] || { echo "Compose file not found: $COMPOSE_FILE" >&2; exit 1; }
[[ -f "$BACKUP_FILE" ]] || { echo "Backup file not found: $BACKUP_FILE" >&2; exit 1; }
[[ -f "$AGE_IDENTITY" ]] || { echo "Age identity file not found: $AGE_IDENTITY" >&2; exit 1; }
[[ "$RESTORE_DATABASE" =~ ^[a-zA-Z][a-zA-Z0-9_]{0,62}$ ]] || {
  echo "RESTORE_DATABASE must be a valid, separate PostgreSQL database name." >&2
  exit 1
}

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

BACKUP_DIR="$(cd "$(dirname "$BACKUP_FILE")" && pwd)"
BACKUP_NAME="$(basename "$BACKUP_FILE")"
(
  cd "$BACKUP_DIR"
  sha256sum --check "$BACKUP_NAME.sha256"
)

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/timedrop-restore.XXXXXX")"
PLAIN_FILE="$TMP_DIR/restore.dump"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

echo "Decrypting backup into a protected temporary directory..."
age --decrypt --identity "$AGE_IDENTITY" --output "$PLAIN_FILE" "$BACKUP_FILE"

echo "Validating PostgreSQL archive..."
compose exec -T db pg_restore --list < "$PLAIN_FILE" > /dev/null

echo "Creating isolated restore-test database: $RESTORE_DATABASE"
compose exec -T db createdb --username="$POSTGRES_USER" "$RESTORE_DATABASE"

echo "Restoring archive..."
compose exec -T db pg_restore --exit-on-error --no-owner --no-acl --username="$POSTGRES_USER" --dbname="$RESTORE_DATABASE" < "$PLAIN_FILE"

TABLE_COUNT="$(compose exec -T db psql --username="$POSTGRES_USER" --dbname="$RESTORE_DATABASE" --tuples-only --no-align --command="SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';" | tr -d '[:space:]')"
if [[ ! "$TABLE_COUNT" =~ ^[0-9]+$ ]] || (( TABLE_COUNT < 1 )); then
  echo "Restore verification failed: no public tables were found." >&2
  exit 1
fi

if ! REVISION="$(compose exec -T db psql --username="$POSTGRES_USER" --dbname="$RESTORE_DATABASE" --tuples-only --no-align --command="SELECT version_num FROM alembic_version LIMIT 1;" | tr -d '[:space:]')"; then
  echo "Restore verification failed: Alembic revision could not be read." >&2
  exit 1
fi
if [[ -z "$REVISION" ]]; then
  echo "Restore verification failed: Alembic revision is empty." >&2
  exit 1
fi

echo "Restore verification passed."
echo "Database: $RESTORE_DATABASE"
echo "Public tables: $TABLE_COUNT"
echo "Alembic revision: $REVISION"
echo "This isolated database was not connected to the application. Review it before planning any production recovery."
