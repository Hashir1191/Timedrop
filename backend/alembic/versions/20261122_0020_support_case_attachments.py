"""Add private evidence attachments to support cases.

Revision ID: 20261122_0020
Revises: 20261122_0019
"""
from alembic import op
import sqlalchemy as sa

revision = "20261122_0020"
down_revision = "20261122_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("support_case_attachments"):
        op.create_table(
            "support_case_attachments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("case_id", sa.Integer(), sa.ForeignKey("support_cases.id", ondelete="CASCADE"), nullable=False),
            sa.Column("uploader_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("filename", sa.String(length=180), nullable=False),
            sa.Column("content_type", sa.String(length=80), nullable=False),
            sa.Column("file_size", sa.Integer(), nullable=False),
            sa.Column("sha256", sa.String(length=64), nullable=False),
            sa.Column("is_internal", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("file_content", sa.LargeBinary(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    indexes = {item["name"] for item in sa.inspect(bind).get_indexes("support_case_attachments")}
    for name, columns in (
        ("ix_support_case_attachments_id", ["id"]),
        ("ix_support_case_attachments_case_id", ["case_id"]),
        ("ix_support_case_attachments_uploader_id", ["uploader_id"]),
    ):
        if name not in indexes:
            op.create_index(name, "support_case_attachments", columns, unique=False)


def downgrade() -> None:
    op.drop_index("ix_support_case_attachments_uploader_id", table_name="support_case_attachments")
    op.drop_index("ix_support_case_attachments_case_id", table_name="support_case_attachments")
    op.drop_index("ix_support_case_attachments_id", table_name="support_case_attachments")
    op.drop_table("support_case_attachments")
