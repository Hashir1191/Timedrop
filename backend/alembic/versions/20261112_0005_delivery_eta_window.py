"""Add customer-visible estimated delivery window.

Revision ID: 20261112_0005
Revises: 20261112_0004
"""
from alembic import op
import sqlalchemy as sa

revision = "20261112_0005"
down_revision = "20261112_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "delivery_assignments",
        sa.Column("estimated_delivery_start", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "delivery_assignments",
        sa.Column("estimated_delivery_end", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("delivery_assignments", "estimated_delivery_end")
    op.drop_column("delivery_assignments", "estimated_delivery_start")
