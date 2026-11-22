"""Add verifiable printable parcel registration documents.

Revision ID: 20261122_0018
Revises: 20261122_0017
"""
from alembic import op
import sqlalchemy as sa

revision = "20261122_0018"
down_revision = "20261122_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("parcel_documents"):
        op.create_table(
            "parcel_documents",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("parcel_id", sa.Integer(), sa.ForeignKey("parcels.id", ondelete="CASCADE"), nullable=False),
            sa.Column("document_type", sa.String(length=40), nullable=False),
            sa.Column("document_number", sa.String(length=32), nullable=False, unique=True),
            sa.Column("verification_code", sa.String(length=40), nullable=False, unique=True),
            sa.Column("sha256", sa.String(length=64), nullable=False),
            sa.Column("pdf_content", sa.LargeBinary(), nullable=False),
            sa.Column("generated_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    indexes = {item["name"] for item in sa.inspect(bind).get_indexes("parcel_documents")}
    for name, columns in (
        ("ix_parcel_documents_id", ["id"]),
        ("ix_parcel_documents_parcel_id", ["parcel_id"]),
        ("ix_parcel_documents_document_type", ["document_type"]),
        ("ix_parcel_documents_document_number", ["document_number"]),
        ("ix_parcel_documents_verification_code", ["verification_code"]),
    ):
        if name not in indexes:
            op.create_index(name, "parcel_documents", columns, unique=False)


def downgrade() -> None:
    op.drop_index("ix_parcel_documents_verification_code", table_name="parcel_documents")
    op.drop_index("ix_parcel_documents_document_number", table_name="parcel_documents")
    op.drop_index("ix_parcel_documents_document_type", table_name="parcel_documents")
    op.drop_index("ix_parcel_documents_parcel_id", table_name="parcel_documents")
    op.drop_index("ix_parcel_documents_id", table_name="parcel_documents")
    op.drop_table("parcel_documents")
