# Phase 35 — Encrypted PostgreSQL backup and restore verification

## Backup design

The backup script uses PostgreSQL's custom archive format, validates the archive with pg_restore, encrypts it with age, and writes a SHA-256 checksum beside the encrypted file. Plaintext dumps are created only in a protected temporary directory and removed on exit.

Optional off-site copying uses an already-configured rclone remote. The script uploads only the encrypted archive and its checksum.

## Prerequisites

- Docker Engine and Docker Compose.
- age installed on the deployment host.
- An age public recipient for backups and the corresponding private identity stored separately from the backup destination.
- A running production Compose stack and a protected deployment .env file.
- Optional: rclone configured with a restricted remote destination.

Generate an age identity and keep its private key in a secrets manager or offline recovery location. Do not commit it to the repository or store it beside the backups. Set BACKUP_AGE_RECIPIENT to its public recipient.

## Create a backup

From the repository root:

~~~bash
export BACKUP_AGE_RECIPIENT='age1...'
export BACKUP_DIR='/var/backups/timedrop'
# Optional off-site destination, for example a configured rclone remote:
export BACKUP_REMOTE='s3:private-timedrop-backups/production'

bash scripts/backup_postgres.sh
~~~

The resulting .dump.age file is encrypted. The .sha256 file verifies its integrity. If BACKUP_REMOTE is set, both files are copied to that remote. Configure remote-side encryption, access restrictions, object versioning, and lifecycle retention independently.

Schedule the script with the host's scheduler (for example, a daily cron job) and monitor its exit status and remote-copy result. Keep backups off the application host. Define retention according to business and legal requirements; do not rely on the local Docker volume as a backup.

## Verify a restore without overwriting production

The restore script requires explicit confirmation and creates a NEW, separately named database. It refuses to drop or overwrite an existing database. It verifies the checksum, decrypts into a protected temporary directory, validates the archive, restores it, and checks that public tables and an Alembic revision exist.

~~~bash
export BACKUP_FILE='/var/backups/timedrop/timedrop-postgres-YYYYMMDDTHHMMSSZ.dump.age'
export AGE_IDENTITY='/secure/path/to/age-identity.txt'
export RESTORE_DATABASE='timedrop_restore_check'
export CONFIRM_RESTORE='YES'

bash scripts/restore_postgres_backup.sh
~~~

Inspect the restored database using a database client before declaring the backup recoverable. A successful restore test does not automatically switch the live application to that database. Keep the original production database unchanged during verification.

To repeat a restore test, choose a new RESTORE_DATABASE name. The script intentionally does not delete old test databases.

## Recovery procedure

1. Put the application into a maintenance window and stop writes.
2. Preserve the current database and relevant logs before attempting recovery.
3. Select a verified encrypted backup and confirm its checksum.
4. Restore it to a separate database using the verification script.
5. Validate critical records, migration revision, counts, and application-specific invariants with the operations owner.
6. Plan a controlled database cutover using a separately reviewed runbook and fresh backup.
7. Confirm API readiness and perform customer, operations, and partner smoke checks before reopening traffic.

Do not point the live application at a restored database until the data owner approves the recovery point and cutover plan.

## Security and operational notes

- Keep the age private identity separate from encrypted backup storage.
- Restrict backup directory permissions; the script sets a private umask and directory mode.
- Do not email backup files or place them in public object storage.
- Monitor scheduled job failures and periodically perform restore drills.
- A checksum detects accidental corruption; it is not a substitute for authenticated encryption or access control.
- Backups may contain personal data. Apply retention, deletion, access, and data residency requirements to both local and remote copies.
- Never use docker compose down -v as a cleanup step on a database containing data you need.
