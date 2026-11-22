"""Add privacy-scoped live delivery location telemetry.

Revision ID: 20261122_0016
Revises: 20261116_0015
"""
from alembic import op
import sqlalchemy as sa

revision = "20261122_0016"
down_revision = "20261116_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("delivery_location_updates"):
        op.create_table(
            "delivery_location_updates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "assignment_id",
                sa.Integer(),
                sa.ForeignKey("delivery_assignments.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("latitude", sa.Float(), nullable=False),
            sa.Column("longitude", sa.Float(), nullable=False),
            sa.Column("accuracy_meters", sa.Float(), nullable=True),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        )
    indexes = {item["name"] for item in sa.inspect(bind).get_indexes("delivery_location_updates")}
    for name, columns in (
        ("ix_delivery_location_updates_id", ["id"]),
        ("ix_delivery_location_updates_assignment_id", ["assignment_id"]),
        ("ix_delivery_location_updates_recorded_at", ["recorded_at"]),
    ):
        if name not in indexes:
            op.create_index(name, "delivery_location_updates", columns, unique=False)


def downgrade() -> None:
    op.drop_index("ix_delivery_location_updates_recorded_at", table_name="delivery_location_updates")
    op.drop_index("ix_delivery_location_updates_assignment_id", table_name="delivery_location_updates")
    op.drop_index("ix_delivery_location_updates_id", table_name="delivery_location_updates")
    op.drop_table("delivery_location_updates")
