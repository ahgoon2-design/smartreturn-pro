"""add return hold followup fields

Revision ID: 4c8e1a7b9d02
Revises: 3b7d2e9f4a61
Create Date: 2026-06-05 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "4c8e1a7b9d02"
down_revision: str | Sequence[str] | None = "3b7d2e9f4a61"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "return_intake_rows",
        sa.Column("hold_status", sa.String(length=50), server_default="HOLD_PENDING", nullable=False),
    )
    op.add_column("return_intake_rows", sa.Column("hold_reason", sa.Text(), nullable=True))
    op.add_column("return_intake_rows", sa.Column("hold_response_memo", sa.Text(), nullable=True))
    op.add_column("return_intake_rows", sa.Column("hold_resolved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("return_intake_rows", sa.Column("hold_resolved_by", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_return_intake_rows_hold_resolved_by",
        "return_intake_rows",
        "users",
        ["hold_resolved_by"],
        ["id"],
    )
    op.create_index(
        "ix_return_intake_rows_hold",
        "return_intake_rows",
        ["client_id", "hold_status", "judgement_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_return_intake_rows_hold", table_name="return_intake_rows")
    op.drop_constraint("fk_return_intake_rows_hold_resolved_by", "return_intake_rows", type_="foreignkey")
    op.drop_column("return_intake_rows", "hold_resolved_by")
    op.drop_column("return_intake_rows", "hold_resolved_at")
    op.drop_column("return_intake_rows", "hold_response_memo")
    op.drop_column("return_intake_rows", "hold_reason")
    op.drop_column("return_intake_rows", "hold_status")
