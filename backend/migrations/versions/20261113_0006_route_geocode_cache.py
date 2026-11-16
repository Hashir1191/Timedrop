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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("route_geocode_cache"):
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
    indexes = {item["name"] for item in sa.inspect(bind).get_indexes("route_geocode_cache")}
    for name, columns in (
        ("ix_route_geocode_cache_id", ["id"]),
        ("ix_route_geocode_cache_address_hash", ["address_hash"]),
    ):
        if name not in indexes:
            op.create_index(name, "route_geocode_cache", columns, unique=False)


def downgrade() -> None:
    op.drop_index("ix_route_geocode_cache_address_hash", table_name="route_geocode_cache")
    op.drop_index("ix_route_geocode_cache_id", table_name="route_geocode_cache")
    op.drop_table("route_geocode_cache")
