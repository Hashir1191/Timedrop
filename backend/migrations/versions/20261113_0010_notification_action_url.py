"""Add safe in-app notification destinations.

Revision ID: 20261113_0010
Revises: 20261113_0009
"""
from alembic import op
import sqlalchemy as sa

revision = "20261113_0010"
down_revision = "20261113_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("action_url", sa.String(length=240), nullable=True))


def downgrade() -> None:
    op.drop_column("notifications", "action_url")
