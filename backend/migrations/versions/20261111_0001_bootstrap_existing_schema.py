"""Bootstrap the current TimeDrop schema without discarding existing data.

Revision ID: 20261111_0001
Revises:
Create Date: 2026-11-11
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

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

    This one-time baseline/adoption migration creates tables that do not exist,
    while leaving existing tables and rows in place. It then conditionally adds
    the known columns introduced by earlier pilot releases.
    """
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    tables = set(inspect(bind).get_table_names())
    if "parcels" in tables:
        parcel_columns = _columns("parcels")
        if "owner_id" not in parcel_columns:
            if bind.dialect.name == "sqlite":
                # SQLite needs a batch table rebuild to add a foreign-key constraint.
                with op.batch_alter_table("parcels") as batch_op:
                    batch_op.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))
                    batch_op.create_foreign_key(
                        "fk_parcels_owner_id_users", "users", ["owner_id"], ["id"], ondelete="SET NULL"
                    )
            else:
                op.add_column("parcels", sa.Column("owner_id", sa.Integer(), nullable=True))
                op.create_foreign_key(
                    "fk_parcels_owner_id_users", "parcels", "users", ["owner_id"], ["id"], ondelete="SET NULL"
                )
        parcel_indexes = {index["name"] for index in inspect(bind).get_indexes("parcels")}
        if "ix_parcels_owner_id" not in parcel_indexes:
            op.create_index("ix_parcels_owner_id", "parcels", ["owner_id"], unique=False)

    if "delivery_assignments" in tables:
        assignment_columns = _columns("delivery_assignments")
        additions = {
            "failure_reason": sa.Column("failure_reason", sa.String(length=300), nullable=True),
            "delivery_code_hash": sa.Column("delivery_code_hash", sa.String(length=255), nullable=True),
            "delivery_code_expires_at": sa.Column("delivery_code_expires_at", sa.DateTime(), nullable=True),
            "delivery_code_attempts": sa.Column("delivery_code_attempts", sa.Integer(), nullable=False, server_default="0"),
            "delivered_at": sa.Column("delivered_at", sa.DateTime(), nullable=True),
            "proof_recipient_name": sa.Column("proof_recipient_name", sa.String(length=120), nullable=True),
        }
        for column_name, column in additions.items():
            if column_name not in assignment_columns:
                op.add_column("delivery_assignments", column)


def downgrade() -> None:
    """Keep this adoption revision forward-only to protect existing pilot data."""
    pass
