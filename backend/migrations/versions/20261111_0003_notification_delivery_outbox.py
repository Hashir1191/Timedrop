"""Add durable notification delivery outbox."""
from alembic import op
import sqlalchemy as sa

revision = "20261111_0003"
down_revision = "20261111_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("notification_deliveries"):
        op.create_table(
            "notification_deliveries",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("notification_id", sa.Integer(), sa.ForeignKey("notifications.id", ondelete="SET NULL"), nullable=True),
            sa.Column("channel", sa.String(length=16), nullable=False),
            sa.Column("recipient", sa.String(length=255), nullable=False),
            sa.Column("subject", sa.String(length=200), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False, unique=True),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("provider_message_id", sa.String(length=255), nullable=True),
            sa.Column("last_error", sa.String(length=1000), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    inspector = sa.inspect(bind)
    existing = {idx["name"] for idx in inspector.get_indexes("notification_deliveries")}
    for name, column in (("ix_notification_deliveries_id", "id"), ("ix_notification_deliveries_notification_id", "notification_id"), ("ix_notification_deliveries_status", "status"), ("ix_notification_deliveries_next_attempt_at", "next_attempt_at")):
        if name not in existing:
            op.create_index(name, "notification_deliveries", [column], unique=False)


def downgrade() -> None:
    # Preserve delivery audit records; destructive rollback is intentionally disabled.
    pass
