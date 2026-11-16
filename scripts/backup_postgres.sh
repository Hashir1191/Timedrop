#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.production.yml}"
ENV_FILE="${ENV_FILE:-.env}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"

: "${BACKUP_AGE_RECIPIENT:?Set BACKUP_AGE_RECIPIENT to an age public recipient}"

command -v docker >/dev/null 2>&1 || { echo "docker is required." >&2; exit 1; }
command -v age >/dev/null 2>&1 || { echo "age is required for encrypted backups." >&2; exit 1; }
[[ -f "$ENV_FILE" ]] || { echo "Environment file not found: $ENV_FILE" >&2; exit 1; }
[[ -f "$COMPOSE_FILE" ]] || { echo "Compose file not found: $COMPOSE_FILE" >&2; exit 1; }

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
BACKUP_DIR="$(cd "$BACKUP_DIR" && pwd)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
NAME="timedrop-postgres-$STAMP"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/timedrop-backup.XXXXXX")"
PLAIN_FILE="$TMP_DIR/$NAME.dump"
ENCRYPTED_FILE="$BACKUP_DIR/$NAME.dump.age"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

echo "Creating PostgreSQL custom-format backup..."
compose exec -T db sh -c 'exec pg_dump --format=custom --no-owner --no-acl --username="$POSTGRES_USER" "$POSTGRES_DB"' > "$PLAIN_FILE"

if [[ ! -s "$PLAIN_FILE" ]]; then
  echo "The database dump is empty; refusing to publish a backup." >&2
  exit 1
fi

echo "Validating PostgreSQL archive..."
compose exec -T db pg_restore --list < "$PLAIN_FILE" > /dev/null

echo "Encrypting backup with age..."
age --recipient "$BACKUP_AGE_RECIPIENT" --output "$ENCRYPTED_FILE" "$PLAIN_FILE"
chmod 600 "$ENCRYPTED_FILE"

(
  cd "$BACKUP_DIR"
  sha256sum "$(basename "$ENCRYPTED_FILE")" > "$(basename "$ENCRYPTED_FILE").sha256"
)

if [[ -n "${BACKUP_REMOTE:-}" ]]; then
  command -v rclone >/dev/null 2>&1 || { echo "BACKUP_REMOTE is set but rclone is not installed." >&2; exit 1; }
  echo "Copying encrypted backup and checksum to configured remote..."
  rclone copy "$ENCRYPTED_FILE" "$BACKUP_REMOTE"
  rclone copy "$ENCRYPTED_FILE.sha256" "$BACKUP_REMOTE"
fi

echo "Backup created: $ENCRYPTED_FILE"
echo "Checksum: $ENCRYPTED_FILE.sha256"
