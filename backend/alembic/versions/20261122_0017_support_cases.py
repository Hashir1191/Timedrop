"""Add customer support cases, replies and lifecycle events.

Revision ID: 20261122_0017
Revises: 20261122_0016
"""
from alembic import op
import sqlalchemy as sa

revision = "20261122_0017"
down_revision = "20261122_0016"
branch_labels = None
depends_on = None


def _create_indexes(table_name, indexes):
    existing = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes(table_name)}
    for name, columns in indexes:
        if name not in existing:
            op.create_index(name, table_name, columns, unique=False)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("support_cases"):
        op.create_table(
            "support_cases",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("case_number", sa.String(length=24), nullable=False, unique=True),
            sa.Column("customer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("parcel_id", sa.Integer(), sa.ForeignKey("parcels.id", ondelete="SET NULL"), nullable=True),
            sa.Column("category", sa.String(length=32), nullable=False),
            sa.Column("subject", sa.String(length=160), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=24), nullable=False, server_default="open"),
            sa.Column("priority", sa.String(length=16), nullable=False, server_default="normal"),
            sa.Column("assigned_to_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not inspector.has_table("support_case_messages"):
        op.create_table(
            "support_case_messages",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("case_id", sa.Integer(), sa.ForeignKey("support_cases.id", ondelete="CASCADE"), nullable=False),
            sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("is_internal", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not inspector.has_table("support_case_events"):
        op.create_table(
            "support_case_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("case_id", sa.Integer(), sa.ForeignKey("support_cases.id", ondelete="CASCADE"), nullable=False),
            sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("event_type", sa.String(length=32), nullable=False),
            sa.Column("from_status", sa.String(length=24), nullable=True),
            sa.Column("to_status", sa.String(length=24), nullable=True),
            sa.Column("note", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    _create_indexes("support_cases", [
        ("ix_support_cases_id", ["id"]),
        ("ix_support_cases_case_number", ["case_number"]),
        ("ix_support_cases_customer_id", ["customer_id"]),
        ("ix_support_cases_parcel_id", ["parcel_id"]),
        ("ix_support_cases_status", ["status"]),
        ("ix_support_cases_priority", ["priority"]),
        ("ix_support_cases_assigned_to_id", ["assigned_to_id"]),
    ])
    _create_indexes("support_case_messages", [
        ("ix_support_case_messages_id", ["id"]),
        ("ix_support_case_messages_case_id", ["case_id"]),
        ("ix_support_case_messages_author_id", ["author_id"]),
    ])
    _create_indexes("support_case_events", [
        ("ix_support_case_events_id", ["id"]),
        ("ix_support_case_events_case_id", ["case_id"]),
        ("ix_support_case_events_actor_id", ["actor_id"]),
    ])


def downgrade() -> None:
    for name, table in (
        ("ix_support_case_events_actor_id", "support_case_events"),
        ("ix_support_case_events_case_id", "support_case_events"),
        ("ix_support_case_events_id", "support_case_events"),
        ("ix_support_case_messages_author_id", "support_case_messages"),
        ("ix_support_case_messages_case_id", "support_case_messages"),
        ("ix_support_case_messages_id", "support_case_messages"),
        ("ix_support_cases_assigned_to_id", "support_cases"),
        ("ix_support_cases_priority", "support_cases"),
        ("ix_support_cases_status", "support_cases"),
        ("ix_support_cases_parcel_id", "support_cases"),
        ("ix_support_cases_customer_id", "support_cases"),
        ("ix_support_cases_case_number", "support_cases"),
        ("ix_support_cases_id", "support_cases"),
    ):
        op.drop_index(name, table_name=table)
    op.drop_table("support_case_events")
    op.drop_table("support_case_messages")
    op.drop_table("support_cases")
