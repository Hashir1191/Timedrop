"""Add verified phone numbers and SMS consent."""
from alembic import op
import sqlalchemy as sa

revision = "20261112_0004"
down_revision = "20261111_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "phone_number" not in user_columns:
        op.add_column("users", sa.Column("phone_number", sa.String(length=16), nullable=True))
    if "phone_verified_at" not in user_columns:
        op.add_column("users", sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=True))
    if "sms_consent_at" not in user_columns:
        op.add_column("users", sa.Column("sms_consent_at", sa.DateTime(timezone=True), nullable=True))

    indexes = {item["name"] for item in sa.inspect(bind).get_indexes("users")}
    if "ix_users_phone_number" not in indexes:
        op.create_index("ix_users_phone_number", "users", ["phone_number"], unique=True)

    if not sa.inspect(bind).has_table("phone_verification_codes"):
        op.create_table(
            "phone_verification_codes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("phone_number", sa.String(length=16), nullable=False),
            sa.Column("code_hash", sa.String(length=255), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    code_indexes = {item["name"] for item in sa.inspect(bind).get_indexes("phone_verification_codes")}
    for name, column in (
        ("ix_phone_verification_codes_id", "id"),
        ("ix_phone_verification_codes_user_id", "user_id"),
        ("ix_phone_verification_codes_expires_at", "expires_at"),
    ):
        if name not in code_indexes:
            op.create_index(name, "phone_verification_codes", [column], unique=False)


def downgrade() -> None:
    # Retain verification audit data and user phone/consent state on rollback.
    pass
