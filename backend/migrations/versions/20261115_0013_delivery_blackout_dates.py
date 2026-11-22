
"""Add operations-managed delivery blackout dates.

Revision ID: 20261115_0013
Revises: 20261115_0012
"""

from alembic import op
import sqlalchemy as sa


revision = "20261115_0013"
down_revision = "20261115_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Create the blackout dates table if it does not exist.
    if not inspector.has_table("delivery_blackout_dates"):
        op.create_table(
            "delivery_blackout_dates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "delivery_date",
                sa.Date(),
                nullable=False,
            ),
            sa.Column(
                "reason",
                sa.String(length=255),
                nullable=False,
            ),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
            sa.Column(
                "created_by_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
            ),
            sa.UniqueConstraint(
                "delivery_date",
                name="uq_delivery_blackout_date",
            ),
        )

    # Create the delivery_date index if it does not exist.
    inspector = sa.inspect(bind)

    existing_indexes = {
        index["name"]
        for index in inspector.get_indexes("delivery_blackout_dates")
    }

    index_name = "ix_delivery_blackout_dates_delivery_date"

    if index_name not in existing_indexes:
        op.create_index(
            index_name,
            "delivery_blackout_dates",
            ["delivery_date"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("delivery_blackout_dates"):
        existing_indexes = {
            index["name"]
            for index in inspector.get_indexes("delivery_blackout_dates")
        }

        index_name = "ix_delivery_blackout_dates_delivery_date"

        if index_name in existing_indexes:
            op.drop_index(
                index_name,
                table_name="delivery_blackout_dates",
            )

        op.drop_table("delivery_blackout_dates")
