"""Bootstrap the current TimeDrop schema without discarding existing data.

Revision ID: 20261111_0001
Revises:
Create Date: 2026-11-11
"""
from alembic import op
from sqlalchemy import inspect, text

from app.database import Base
from app import models  # noqa: F401 - register all current tables


revision = "20261111_0001"
down_revision = None
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    """Create missing tables, then add fields introduced by earlier app versions.

    This is a one-time baseline/adoption migration. It deliberately uses the
    current SQLAlchemy metadata to create tables that do not exist, while leaving
    existing tables and their rows untouched. The conditional ALTER statements
    bring older SQLite pilot databases up to the current model shape.
    """
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    tables = set(inspect(bind).get_table_names())
    if "parcels" in tables:
        parcel_columns = _columns("parcels")
        if "owner_id" not in parcel_columns:
            op.execute(text(
                "ALTER TABLE parcels ADD COLUMN owner_id INTEGER "
                "REFERENCES users(id) ON DELETE SET NULL"
            ))
        parcel_indexes = {index["name"] for index in inspect(bind).get_indexes("parcels")}
        if "ix_parcels_owner_id" not in parcel_indexes:
            op.create_index("ix_parcels_owner_id", "parcels", ["owner_id"], unique=False)

    if "delivery_assignments" in tables:
        assignment_columns = _columns("delivery_assignments")
        additions = {
            "failure_reason": "VARCHAR(300)",
            "delivery_code_hash": "VARCHAR(255)",
            "delivery_code_expires_at": "DATETIME",
            "delivery_code_attempts": "INTEGER NOT NULL DEFAULT 0",
            "delivered_at": "DATETIME",
            "proof_recipient_name": "VARCHAR(120)",
        }
        for column_name, sql_type in additions.items():
            if column_name not in assignment_columns:
                op.execute(text(
                    f"ALTER TABLE delivery_assignments ADD COLUMN {column_name} {sql_type}"
                ))


def downgrade() -> None:
    """Do not drop application data in a baseline adoption migration.

    This revision may be stamped onto a database containing live pilot records.
    A destructive downgrade would be unsafe; forward-only schema evolution is
    intentional for this bootstrap revision.
    """
    pass
