"""Copy a migrated TimeDrop SQLite database into an empty PostgreSQL database.

This utility is intentionally explicit and conservative:
- SQLite is opened read-only.
- Both databases must be at the same Alembic revision.
- Business table names and columns must match exactly.
- The PostgreSQL target must contain zero rows in every business table.
- No data is written unless --execute is supplied.
- All inserts run in one PostgreSQL transaction.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import MetaData, create_engine, func, inspect, select, text
from sqlalchemy.engine import Engine


ALEMBIC_VERSION_TABLE = "alembic_version"
BATCH_SIZE = 500


def read_revision(engine: Engine) -> str:
    inspector = inspect(engine)
    if ALEMBIC_VERSION_TABLE not in inspector.get_table_names():
        raise RuntimeError("Database has no Alembic version table. Apply migrations first.")
    with engine.connect() as connection:
        revision = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one_or_none()
    if not revision:
        raise RuntimeError("Database has no recorded Alembic revision. Apply migrations first.")
    return revision


def dependency_order(metadata: MetaData) -> list[str]:
    """Return parent-before-child order; reject cyclic foreign-key dependencies."""
    names = set(metadata.tables)
    dependencies: dict[str, set[str]] = {name: set() for name in names}
    for table in metadata.tables.values():
        for foreign_key in table.foreign_keys:
            parent = foreign_key.column.table.fullname
            if parent in names and parent != table.fullname:
                dependencies[table.fullname].add(parent)

    ordered: list[str] = []
    remaining = {name: set(parents) for name, parents in dependencies.items()}
    while remaining:
        ready = sorted(name for name, parents in remaining.items() if not parents)
        if not ready:
            cycle_names = ", ".join(sorted(remaining))
            raise RuntimeError(
                "Foreign-key cycle detected; refusing automatic copy for: " + cycle_names
            )
        for name in ready:
            ordered.append(name)
            remaining.pop(name)
        for parents in remaining.values():
            parents.difference_update(ready)
    return ordered


def reflect_business_tables(engine: Engine) -> MetaData:
    metadata = MetaData()
    names = [
        name for name in inspect(engine).get_table_names()
        if name != ALEMBIC_VERSION_TABLE
    ]
    metadata.reflect(bind=engine, only=names)
    return metadata


def preflight(source: Engine, target: Engine) -> tuple[MetaData, MetaData, list[str], dict[str, int]]:
    if source.dialect.name != "sqlite":
        raise RuntimeError("Source database must be SQLite.")
    if target.dialect.name != "postgresql":
        raise RuntimeError("Target database must be PostgreSQL.")

    source_revision = read_revision(source)
    target_revision = read_revision(target)
    if source_revision != target_revision:
        raise RuntimeError(
            f"Alembic revisions differ (SQLite={source_revision}, PostgreSQL={target_revision}). "
            "Migrate both databases to the same revision before copying."
        )

    source_meta = reflect_business_tables(source)
    target_meta = reflect_business_tables(target)
    source_names = set(source_meta.tables)
    target_names = set(target_meta.tables)
    if source_names != target_names:
        missing = sorted(source_names - target_names)
        extra = sorted(target_names - source_names)
        raise RuntimeError(
            f"Business table sets differ. Missing in PostgreSQL: {missing}; "
            f"extra in PostgreSQL: {extra}."
        )

    counts: dict[str, int] = {}
    with source.connect() as source_connection, target.connect() as target_connection:
        for name in sorted(source_names):
            source_table = source_meta.tables[name]
            target_table = target_meta.tables[name]
            source_columns = {column.name for column in source_table.columns}
            target_columns = {column.name for column in target_table.columns}
            if source_columns != target_columns:
                raise RuntimeError(
                    f"Column mismatch in {name}. SQLite={sorted(source_columns)}; "
                    f"PostgreSQL={sorted(target_columns)}."
                )
            counts[name] = source_connection.execute(
                select(func.count()).select_from(source_table)
            ).scalar_one()
            target_count = target_connection.execute(
                select(func.count()).select_from(target_table)
            ).scalar_one()
            if target_count != 0:
                raise RuntimeError(
                    f"Target table {name} is not empty ({target_count} rows). "
                    "Refusing to overwrite or mix data."
                )

    order = dependency_order(source_meta)
    return source_meta, target_meta, order, counts


def copy_rows(
    source: Engine,
    target: Engine,
    source_meta: MetaData,
    target_meta: MetaData,
    order: list[str],
) -> dict[str, int]:
    copied: dict[str, int] = {}
    with source.connect() as source_connection, target.begin() as target_connection:
        for name in order:
            source_table = source_meta.tables[name]
            target_table = target_meta.tables[name]
            result = source_connection.execution_options(stream_results=True).execute(
                select(source_table)
            )
            total = 0
            for batch in result.mappings().partitions(BATCH_SIZE):
                rows = [dict(row) for row in batch]
                if rows:
                    target_connection.execute(target_table.insert(), rows)
                    total += len(rows)
            copied[name] = total

        # Verify persisted row counts before the transaction is allowed to commit.
        for name, expected_count in copied.items():
            actual_count = target_connection.execute(
                select(func.count()).select_from(target_meta.tables[name])
            ).scalar_one()
            if actual_count != expected_count:
                raise RuntimeError(
                    f"Verification failed for {name}: expected {expected_count}, found {actual_count}."
                )

        # Preserve explicit integer primary keys and advance PostgreSQL sequences.
        for name in order:
            table = target_meta.tables[name]
            primary_key = list(table.primary_key.columns)
            if len(primary_key) != 1:
                continue
            column = primary_key[0]
            if not isinstance(column.type.python_type, type) or column.type.python_type is not int:
                continue
            max_id = target_connection.execute(
                select(func.max(column))
            ).scalar_one()
            if max_id is None:
                continue
            target_connection.execute(
                text(
                    "SELECT setval(pg_get_serial_sequence(:table_name, :column_name), "
                    ":last_value, true)"
                ),
                {
                    "table_name": f"{table.schema or 'public'}.{table.name}",
                    "column_name": column.name,
                    "last_value": max_id,
                },
            )
    return copied


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Safely copy TimeDrop data from SQLite into an empty PostgreSQL database."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("timedrop.db"),
        help="Path to the migrated SQLite database (default: ./timedrop.db).",
    )
    parser.add_argument(
        "--target-url",
        required=True,
        help="PostgreSQL SQLAlchemy URL, e.g. postgresql+psycopg://user:pass@localhost:5432/timedrop.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform the copy. Without this flag, only run read-only preflight checks.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_path = args.source.resolve()
    if not source_path.is_file():
        print(f"SQLite source file does not exist: {source_path}", file=sys.stderr)
        return 2

    source_url = f"sqlite:///{source_path.as_posix()}?mode=ro&uri=true"
    source_engine = create_engine(source_url, connect_args={"check_same_thread": False})
    target_engine = create_engine(args.target_url, pool_pre_ping=True)

    try:
        source_meta, target_meta, order, counts = preflight(source_engine, target_engine)
        total = sum(counts.values())
        print(f"Preflight passed. Matching Alembic revision: {read_revision(source_engine)}")
        print(f"Tables: {len(order)} | Rows to copy: {total}")
        for name in order:
            print(f"  {name}: {counts[name]} rows")

        if not args.execute:
            print("Dry run only: no PostgreSQL data was changed. Re-run with --execute to copy.")
            return 0

        copied = copy_rows(source_engine, target_engine, source_meta, target_meta, order)
        if copied != counts:
            raise RuntimeError(f"Post-copy row counts differ. Expected {counts}; copied {copied}.")
        print(f"Copy committed successfully. Total rows copied: {sum(copied.values())}")
        return 0
    except Exception as exc:
        print(f"Migration stopped: {exc}", file=sys.stderr)
        return 1
    finally:
        source_engine.dispose()
        target_engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
