"""Add operations-managed serviceable PIN codes.

Revision ID: 20261115_0012
Revises: 20261113_0011
"""
from alembic import op
import sqlalchemy as sa

revision = "20261115_0012"
down_revision = "20261113_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "serviceable_pincodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pincode", sa.String(length=6), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("pincode", name="uq_serviceable_pincodes_pincode"),
    )
    op.create_index(
        "ix_serviceable_pincodes_pincode",
        "serviceable_pincodes",
        ["pincode"],
    )
    op.alter_column("serviceable_pincodes", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_serviceable_pincodes_pincode", table_name="serviceable_pincodes")
    op.drop_table("serviceable_pincodes")
