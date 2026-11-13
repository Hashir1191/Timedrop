"""Add persistent geocoding cache for route planning.

Revision ID: 20261113_0006
Revises: 20261112_0005
"""
from alembic import op
import sqlalchemy as sa

revision = "20261113_0006"
down_revision = "20261112_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "route_geocode_cache",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("address_hash", sa.String(length=64), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("address_hash", name="uq_route_geocode_cache_address_hash"),
    )
    op.create_index("ix_route_geocode_cache_id", "route_geocode_cache", ["id"])
    op.create_index("ix_route_geocode_cache_address_hash", "route_geocode_cache", ["address_hash"])


def downgrade() -> None:
    op.drop_index("ix_route_geocode_cache_address_hash", table_name="route_geocode_cache")
    op.drop_index("ix_route_geocode_cache_id", table_name="route_geocode_cache")
    op.drop_table("route_geocode_cache")
