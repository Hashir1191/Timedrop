"""Add the in-app notifications inbox.

Revision ID: 20261111_0002
Revises: 20261111_0001
Create Date: 2026-11-11
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20261111_0002"
down_revision = "20261111_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    # The bootstrap/adoption migration creates current metadata on a fresh
    # database, so this guard also makes this revision safe in that case.
    if "notifications" not in tables:
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("parcel_id", sa.Integer(), sa.ForeignKey("parcels.id", ondelete="SET NULL"), nullable=True),
            sa.Column("event_type", sa.String(length=50), nullable=False),
            sa.Column("title", sa.String(length=160), nullable=False),
            sa.Column("message", sa.String(length=500), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        )
    indexes = {index["name"] for index in inspect(bind).get_indexes("notifications")}
    if "ix_notifications_user_id" not in indexes:
        op.create_index("ix_notifications_user_id", "notifications", ["user_id"], unique=False)
    if "ix_notifications_created_at" not in indexes:
        op.create_index("ix_notifications_created_at", "notifications", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
