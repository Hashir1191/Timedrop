"""Add merchant applications and approval lifecycle.

Revision ID: 20261125_0016
Revises: 20261116_0015
"""
from alembic import op
import sqlalchemy as sa

revision = "20261125_0016"
down_revision = "20261116_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("merchant_applications"):
        op.create_table(
            "merchant_applications",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("business_name", sa.String(length=160), nullable=False),
            sa.Column("business_type", sa.String(length=80), nullable=False),
            sa.Column("contact_name", sa.String(length=120), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False, unique=True),
            sa.Column("phone_number", sa.String(length=16), nullable=False),
            sa.Column("pickup_address", sa.String(length=255), nullable=False),
            sa.Column("pickup_city", sa.String(length=100), nullable=False),
            sa.Column("pickup_state", sa.String(length=100), nullable=False),
            sa.Column("pickup_pincode", sa.String(length=6), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("review_note", sa.String(length=500), nullable=True),
            sa.Column("reviewed_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    indexes = {item["name"] for item in sa.inspect(bind).get_indexes("merchant_applications")}
    for name, columns in (
        ("ix_merchant_applications_id", ["id"]),
        ("ix_merchant_applications_user_id", ["user_id"]),
        ("ix_merchant_applications_status", ["status"]),
    ):
        if name not in indexes:
            op.create_index(name, "merchant_applications", columns, unique=False)


def downgrade() -> None:
    op.drop_index("ix_merchant_applications_status", table_name="merchant_applications")
    op.drop_index("ix_merchant_applications_user_id", table_name="merchant_applications")
    op.drop_index("ix_merchant_applications_id", table_name="merchant_applications")
    op.drop_table("merchant_applications")
