# Phase 50 — SQLite migration portability and database parity

## Goal

Make the complete Alembic migration chain runnable on both the existing SQLite local-development setup and PostgreSQL, and add an automated SQLite migration job so this regression is caught before merge.

## Changes

- Remove SQLite-incompatible `ALTER TABLE ... ALTER COLUMN ... DROP DEFAULT` operations from historical revisions 0011, 0012, and 0013.
- Retain the declared server defaults. They are compatible with SQLite and preserve safe defaults for inserts that omit those fields.
- Keep revision identifiers and parent links unchanged; this is a portability correction, not a new schema revision.
- Add a dedicated CI job that applies the full migration chain to a fresh SQLite database, verifies the current revision, and repeats `upgrade head` to check idempotence.
- Keep the existing PostgreSQL 16 migration job as a separate cross-database verification.

## Validation

From the repository root on Windows PowerShell:

```powershell
$env:PYTHONPATH = "backend"
$env:DATABASE_URL = "sqlite:///./timedrop-sqlite-migration-check.db"
python -m alembic -c backend\\alembic.ini upgrade head
python -m alembic -c backend\\alembic.ini current
python -m alembic -c backend\\alembic.ini upgrade head
```

Expected revision: `20261116_0015`.

Use a disposable database path for this migration check. Do not point this command at a production database or delete an existing pilot database.

## Scope

This phase does not copy SQLite records into PostgreSQL, alter application endpoints, or deploy the application. The existing Docker Compose PostgreSQL development environment and deliberate SQLite-to-PostgreSQL transfer utility remain separate workflows.
