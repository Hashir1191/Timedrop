"""Add append-only operations audit log.

Revision ID: 20261115_0014
Revises: 20261115_0013
"""
from alembic import op
import sqlalchemy as sa

revision = "20261115_0014"
down_revision = "20261115_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operations_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("summary", sa.String(length=255), nullable=False),
        sa.Column("changed_fields_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_operations_audit_logs_actor_id", "operations_audit_logs", ["actor_id"])
    op.create_index("ix_operations_audit_logs_action", "operations_audit_logs", ["action"])
    op.create_index("ix_operations_audit_logs_entity_type", "operations_audit_logs", ["entity_type"])
    op.create_index("ix_operations_audit_logs_entity_id", "operations_audit_logs", ["entity_id"])
    op.create_index("ix_operations_audit_logs_created_at", "operations_audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_operations_audit_logs_created_at", table_name="operations_audit_logs")
    op.drop_index("ix_operations_audit_logs_entity_id", table_name="operations_audit_logs")
    op.drop_index("ix_operations_audit_logs_entity_type", table_name="operations_audit_logs")
    op.drop_index("ix_operations_audit_logs_action", table_name="operations_audit_logs")
    op.drop_index("ix_operations_audit_logs_actor_id", table_name="operations_audit_logs")
    op.drop_table("operations_audit_logs")
