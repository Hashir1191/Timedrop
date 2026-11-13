"""Add recurring weekly delivery partner availability.

Revision ID: 20261113_0011
Revises: 20261113_0010
"""
from alembic import op
import sqlalchemy as sa

revision = "20261113_0011"
down_revision = "20261113_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "delivery_partners",
        sa.Column("availability_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "delivery_partner_availability",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "partner_id",
            sa.Integer(),
            sa.ForeignKey("delivery_partners.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "partner_id", "weekday", "start_time", "end_time",
            name="uq_partner_availability_window",
        ),
    )
    op.create_index(
        "ix_delivery_partner_availability_partner_id",
        "delivery_partner_availability",
        ["partner_id"],
    )
    op.alter_column("delivery_partners", "availability_enabled", server_default=None)
    op.alter_column("delivery_partner_availability", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_index(
        "ix_delivery_partner_availability_partner_id",
        table_name="delivery_partner_availability",
    )
    op.drop_table("delivery_partner_availability")
    op.drop_column("delivery_partners", "availability_enabled")
