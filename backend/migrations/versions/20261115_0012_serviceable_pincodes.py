
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
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Create the table if it does not already exist.
    if not inspector.has_table("serviceable_pincodes"):
        op.create_table(
            "serviceable_pincodes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "pincode",
                sa.String(length=6),
                nullable=False,
            ),
            sa.Column(
                "city",
                sa.String(length=100),
                nullable=False,
            ),
            sa.Column(
                "state",
                sa.String(length=100),
                nullable=False,
            ),
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
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
            ),
            sa.UniqueConstraint(
                "pincode",
                name="uq_serviceable_pincodes_pincode",
            ),
        )

    # Create the pincode index if it does not already exist.
    inspector = sa.inspect(bind)

    existing_indexes = {
        index["name"]
        for index in inspector.get_indexes("serviceable_pincodes")
    }

    index_name = "ix_serviceable_pincodes_pincode"

    if index_name not in existing_indexes:
        op.create_index(
            index_name,
            "serviceable_pincodes",
            ["pincode"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("serviceable_pincodes"):
        existing_indexes = {
            index["name"]
            for index in inspector.get_indexes("serviceable_pincodes")
        }

        index_name = "ix_serviceable_pincodes_pincode"

        if index_name in existing_indexes:
            op.drop_index(
                index_name,
                table_name="serviceable_pincodes",
            )

        op.drop_table("serviceable_pincodes")
