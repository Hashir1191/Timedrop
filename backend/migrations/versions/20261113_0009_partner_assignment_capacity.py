"""Add configurable active assignment capacity to delivery partners.

Revision ID: 20261113_0009
Revises: 20261113_0008
"""
from alembic import op
import sqlalchemy as sa

revision = "20261113_0009"
down_revision = "20261113_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "delivery_partners",
        sa.Column("max_active_assignments", sa.Integer(), nullable=False, server_default="5"),
    )


def downgrade() -> None:
    op.drop_column("delivery_partners", "max_active_assignments")
