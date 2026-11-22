
"""Add recurring weekly delivery partner availability.

Revision ID: 20261113_0011
Revises: 20261113_0010
"""

from alembic import op
import sqlalchemy as sa

revision = "20261113_0011"
down_revision = "20261113_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Add the availability flag if it is missing.
    partner_columns = {
        column["name"]
        for column in inspector.get_columns("delivery_partners")
    }

    if "availability_enabled" not in partner_columns:
        op.add_column(
            "delivery_partners",
            sa.Column(
                "availability_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )

    # Create the weekly availability table if missing.
    inspector = sa.inspect(bind)

    if not inspector.has_table("delivery_partner_availability"):
        op.create_table(
            "delivery_partner_availability",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "partner_id",
                sa.Integer(),
                sa.ForeignKey("delivery_partners.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("weekday", sa.Integer(), nullable=False),
            sa.Column("start_time", sa.Time(), nullable=False),
            sa.Column("end_time", sa.Time(), nullable=False),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
            ),
            sa.UniqueConstraint(
                "partner_id",
                "weekday",
                "start_time",
                "end_time",
                name="uq_partner_availability_window",
            ),
        )

    # Create the index if it is missing.
    inspector = sa.inspect(bind)

    existing_indexes = {
        index["name"]
        for index in inspector.get_indexes(
            "delivery_partner_availability"
        )
    }

    index_name = "ix_delivery_partner_availability_partner_id"

    if index_name not in existing_indexes:
        op.create_index(
            index_name,
            "delivery_partner_availability",
            ["partner_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("delivery_partner_availability"):
        indexes = {
            index["name"]
            for index in inspector.get_indexes(
                "delivery_partner_availability"
            )
        }

        index_name = "ix_delivery_partner_availability_partner_id"

        if index_name in indexes:
            op.drop_index(
                index_name,
                table_name="delivery_partner_availability",
            )

        op.drop_table("delivery_partner_availability")

    inspector = sa.inspect(bind)

    if inspector.has_table("delivery_partners"):
        columns = {
            column["name"]
            for column in inspector.get_columns("delivery_partners")
        }

        if "availability_enabled" in columns:
            op.drop_column(
                "delivery_partners",
                "availability_enabled",
            )
