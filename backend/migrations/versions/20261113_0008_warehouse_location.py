"""Add warehouse location to parcels.

Revision ID: 20261113_0008
Revises: 20261113_0007
"""
from alembic import op
import sqlalchemy as sa

revision = "20261113_0008"
down_revision = "20261113_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("parcels", sa.Column("warehouse_location", sa.String(length=40), nullable=True))
    op.create_index("ix_parcels_warehouse_location", "parcels", ["warehouse_location"])


def downgrade() -> None:
    op.drop_index("ix_parcels_warehouse_location", table_name="parcels")
    op.drop_column("parcels", "warehouse_location")
