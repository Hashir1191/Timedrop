"""Add operations-managed delivery blackout dates.

Revision ID: 20261115_0013
Revises: 20261115_0012
"""
from alembic import op
import sqlalchemy as sa

revision = "20261115_0013"
down_revision = "20261115_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("delivery_blackout_dates"):
        op.create_table(
            "delivery_blackout_dates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("delivery_date", sa.Date(), nullable=False),
            sa.Column("reason", sa.String(length=255), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("delivery_date", name="uq_delivery_blackout_date"),
        )
    indexes = {item["name"] for item in sa.inspect(bind).get_indexes("delivery_blackout_dates")}
    if "ix_delivery_blackout_dates_delivery_date" not in indexes:
        op.create_index(
            "ix_delivery_blackout_dates_delivery_date",
            "delivery_blackout_dates",
            ["delivery_date"],
        )
    op.alter_column("delivery_blackout_dates", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_index(
        "ix_delivery_blackout_dates_delivery_date",
        table_name="delivery_blackout_dates",
    )
    op.drop_table("delivery_blackout_dates")
