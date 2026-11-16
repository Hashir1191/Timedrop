"""Add notification worker heartbeat state.

Revision ID: 20261116_0015
Revises: 20261115_0014
"""
from alembic import op
import sqlalchemy as sa

revision = "20261116_0015"
down_revision = "20261115_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("worker_heartbeats"):
        op.create_table(
            "worker_heartbeats",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("worker_name", sa.String(length=80), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("worker_name", name="uq_worker_heartbeats_worker_name"),
        )
    indexes = {item["name"] for item in sa.inspect(bind).get_indexes("worker_heartbeats")}
    if "ix_worker_heartbeats_id" not in indexes:
        op.create_index("ix_worker_heartbeats_id", "worker_heartbeats", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_worker_heartbeats_id", table_name="worker_heartbeats")
    op.drop_table("worker_heartbeats")
