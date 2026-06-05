"""add return disposal followup fields

Revision ID: 6e2a9c4d1f03
Revises: 4c8e1a7b9d02
Create Date: 2026-06-05 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "6e2a9c4d1f03"
down_revision: str | Sequence[str] | None = "4c8e1a7b9d02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "return_intake_rows",
        sa.Column("disposal_status", sa.String(length=50), server_default="DISPOSAL_PENDING", nullable=False),
    )
    op.add_column("return_intake_rows", sa.Column("disposal_reason", sa.Text(), nullable=True))
    op.add_column("return_intake_rows", sa.Column("disposal_memo", sa.Text(), nullable=True))
    op.add_column("return_intake_rows", sa.Column("disposal_confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("return_intake_rows", sa.Column("disposal_confirmed_by", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_return_intake_rows_disposal_confirmed_by",
        "return_intake_rows",
        "users",
        ["disposal_confirmed_by"],
        ["id"],
    )
    op.create_index(
        "ix_return_intake_rows_disposal",
        "return_intake_rows",
        ["client_id", "disposal_status", "judgement_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_return_intake_rows_disposal", table_name="return_intake_rows")
    op.drop_constraint("fk_return_intake_rows_disposal_confirmed_by", "return_intake_rows", type_="foreignkey")
    op.drop_column("return_intake_rows", "disposal_confirmed_by")
    op.drop_column("return_intake_rows", "disposal_confirmed_at")
    op.drop_column("return_intake_rows", "disposal_memo")
    op.drop_column("return_intake_rows", "disposal_reason")
    op.drop_column("return_intake_rows", "disposal_status")
