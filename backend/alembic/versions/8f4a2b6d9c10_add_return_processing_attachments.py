"""add return processing attachments

Revision ID: 8f4a2b6d9c10
Revises: 1c7f2c9e8d34
Create Date: 2026-06-02 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "8f4a2b6d9c10"
down_revision: str | Sequence[str] | None = "1c7f2c9e8d34"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "return_processing_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("return_intake_row_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("attachment_type", sa.String(length=50), server_default="PHOTO", nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("active_yn", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["return_intake_batches.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["return_intake_row_id"], ["return_intake_rows.id"]),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_return_processing_attachments_row_active",
        "return_processing_attachments",
        ["return_intake_row_id", "active_yn"],
        unique=False,
    )
    op.create_index(
        "ix_return_processing_attachments_client_uploaded",
        "return_processing_attachments",
        ["client_id", "uploaded_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_return_processing_attachments_client_uploaded", table_name="return_processing_attachments")
    op.drop_index("ix_return_processing_attachments_row_active", table_name="return_processing_attachments")
    op.drop_table("return_processing_attachments")
