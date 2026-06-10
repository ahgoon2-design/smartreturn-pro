"""add return intake tables

Revision ID: 5d5d9c4f3b8e
Revises: 974b73ce4bc9
Create Date: 2026-06-01 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "5d5d9c4f3b8e"
down_revision: str | Sequence[str] | None = "974b73ce4bc9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "return_intake_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("total_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("valid_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("warning_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_return_intake_batches_client_created",
        "return_intake_batches",
        ["client_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_return_intake_batches_status_created",
        "return_intake_batches",
        ["status", "created_at"],
        unique=False,
    )
    op.create_table(
        "return_intake_rows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("row_no", sa.Integer(), nullable=False),
        sa.Column("order_no", sa.String(length=100), nullable=True),
        sa.Column("return_tracking_no", sa.String(length=100), nullable=True),
        sa.Column("original_tracking_no", sa.String(length=100), nullable=True),
        sa.Column("product_code", sa.String(length=80), nullable=True),
        sa.Column("barcode", sa.String(length=100), nullable=True),
        sa.Column("product_name", sa.String(length=255), nullable=True),
        sa.Column("option_name", sa.String(length=255), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=True),
        sa.Column("return_reason", sa.String(length=255), nullable=True),
        sa.Column("customer_name", sa.String(length=100), nullable=True),
        sa.Column("customer_phone_masked", sa.String(length=50), nullable=True),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("validation_status", sa.String(length=50), nullable=False),
        sa.Column("validation_message", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["return_intake_batches.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_id", "row_no", name="uq_return_intake_rows_batch_row_no"),
    )
    op.create_index("ix_return_intake_rows_batch_row_no", "return_intake_rows", ["batch_id", "row_no"], unique=False)
    op.create_index(
        "ix_return_intake_rows_batch_validation",
        "return_intake_rows",
        ["batch_id", "validation_status"],
        unique=False,
    )
    op.create_index("ix_return_intake_rows_client_status", "return_intake_rows", ["client_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_return_intake_rows_client_status", table_name="return_intake_rows")
    op.drop_index("ix_return_intake_rows_batch_validation", table_name="return_intake_rows")
    op.drop_index("ix_return_intake_rows_batch_row_no", table_name="return_intake_rows")
    op.drop_table("return_intake_rows")
    op.drop_index("ix_return_intake_batches_status_created", table_name="return_intake_batches")
    op.drop_index("ix_return_intake_batches_client_created", table_name="return_intake_batches")
    op.drop_table("return_intake_batches")
