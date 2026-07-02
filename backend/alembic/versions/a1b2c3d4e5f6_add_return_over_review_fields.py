"""add return over_review fields to return_intake_rows

Revision ID: a1b2c3d4e5f6
Revises: 3d4e5f6a7b80
Create Date: 2026-06-30 00:00:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "3d4e5f6a7b80"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "return_intake_rows",
        sa.Column("is_over_review_required", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "return_intake_rows",
        sa.Column("over_review_reason", sa.String(length=50), nullable=True),
    )
    op.create_index(
        "ix_return_intake_rows_over_review",
        "return_intake_rows",
        ["client_id", "is_over_review_required"],
    )
    op.create_check_constraint(
        "ck_return_intake_rows_over_review_reason",
        "return_intake_rows",
        "("
        "is_over_review_required = false AND over_review_reason IS NULL"
        ") OR ("
        "is_over_review_required = true AND over_review_reason IN "
        "('QUANTITY_OVER', 'DUPLICATE_SCAN', 'EXPECTED_MISMATCH', 'MANUAL_REVIEW')"
        ")",
    )


def downgrade() -> None:
    op.drop_constraint("ck_return_intake_rows_over_review_reason", "return_intake_rows", type_="check")
    op.drop_index("ix_return_intake_rows_over_review", table_name="return_intake_rows")
    op.drop_column("return_intake_rows", "over_review_reason")
    op.drop_column("return_intake_rows", "is_over_review_required")
