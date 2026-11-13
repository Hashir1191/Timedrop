"""Add append-only parcel custody events.

Revision ID: 20261113_0007
Revises: 20261113_0006
"""
from alembic import op
import sqlalchemy as sa

revision = "20261113_0007"
down_revision = "20261113_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parcel_custody_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("parcel_id", sa.Integer(), sa.ForeignKey("parcels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_type", sa.String(length=24), nullable=False),
        sa.Column("package_condition", sa.String(length=20), nullable=True),
        sa.Column("received_from", sa.String(length=120), nullable=True),
        sa.Column("handed_to", sa.String(length=120), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_parcel_custody_events_parcel_id", "parcel_custody_events", ["parcel_id"])
    op.create_index("ix_parcel_custody_events_id", "parcel_custody_events", ["id"])


def downgrade() -> None:
    op.drop_index("ix_parcel_custody_events_id", table_name="parcel_custody_events")
    op.drop_index("ix_parcel_custody_events_parcel_id", table_name="parcel_custody_events")
    op.drop_table("parcel_custody_events")
