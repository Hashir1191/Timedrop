"""Add signed partner handover acknowledgements.

Revision ID: 20261122_0019
Revises: 20261122_0018
"""
from alembic import op
import sqlalchemy as sa

revision = "20261122_0019"
down_revision = "20261122_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("delivery_handover_signatures"):
        op.create_table(
            "delivery_handover_signatures",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("delivery_assignments.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("parcel_id", sa.Integer(), sa.ForeignKey("parcels.id", ondelete="CASCADE"), nullable=False),
            sa.Column("custody_event_id", sa.Integer(), sa.ForeignKey("parcel_custody_events.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("partner_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("signed_name", sa.String(length=120), nullable=False),
            sa.Column("acknowledgement_text", sa.Text(), nullable=False),
            sa.Column("signature_png", sa.LargeBinary(), nullable=False),
            sa.Column("signature_sha256", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    indexes = {item["name"] for item in sa.inspect(bind).get_indexes("delivery_handover_signatures")}
    for name, columns in (
        ("ix_delivery_handover_signatures_id", ["id"]),
        ("ix_delivery_handover_signatures_assignment_id", ["assignment_id"]),
        ("ix_delivery_handover_signatures_parcel_id", ["parcel_id"]),
        ("ix_delivery_handover_signatures_custody_event_id", ["custody_event_id"]),
        ("ix_delivery_handover_signatures_partner_user_id", ["partner_user_id"]),
    ):
        if name not in indexes:
            op.create_index(name, "delivery_handover_signatures", columns, unique=False)


def downgrade() -> None:
    op.drop_index("ix_delivery_handover_signatures_partner_user_id", table_name="delivery_handover_signatures")
    op.drop_index("ix_delivery_handover_signatures_custody_event_id", table_name="delivery_handover_signatures")
    op.drop_index("ix_delivery_handover_signatures_parcel_id", table_name="delivery_handover_signatures")
    op.drop_index("ix_delivery_handover_signatures_assignment_id", table_name="delivery_handover_signatures")
    op.drop_index("ix_delivery_handover_signatures_id", table_name="delivery_handover_signatures")
    op.drop_table("delivery_handover_signatures")
