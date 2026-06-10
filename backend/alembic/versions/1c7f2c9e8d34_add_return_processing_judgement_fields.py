"""add return processing judgement fields

Revision ID: 1c7f2c9e8d34
Revises: 5d5d9c4f3b8e
Create Date: 2026-06-02 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "1c7f2c9e8d34"
down_revision: str | Sequence[str] | None = "5d5d9c4f3b8e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("return_intake_rows", sa.Column("judgement_status", sa.String(length=50), nullable=True))
    op.add_column("return_intake_rows", sa.Column("judgement_memo", sa.Text(), nullable=True))
    op.add_column("return_intake_rows", sa.Column("judged_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("return_intake_rows", sa.Column("judged_by", sa.Integer(), nullable=True))
    op.add_column("return_intake_rows", sa.Column("return_management_no", sa.String(length=80), nullable=True))
    op.add_column("return_intake_rows", sa.Column("return_label_no", sa.String(length=80), nullable=True))
    op.add_column(
        "return_intake_rows",
        sa.Column("label_print_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("return_intake_rows", sa.Column("label_print_status", sa.String(length=50), nullable=True))
    op.add_column("return_intake_rows", sa.Column("label_printed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_return_intake_rows_judged_by_users",
        "return_intake_rows",
        "users",
        ["judged_by"],
        ["id"],
    )
    op.create_index(
        "ix_return_intake_rows_client_judgement",
        "return_intake_rows",
        ["client_id", "judgement_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_return_intake_rows_client_judgement", table_name="return_intake_rows")
    op.drop_constraint("fk_return_intake_rows_judged_by_users", "return_intake_rows", type_="foreignkey")
    op.drop_column("return_intake_rows", "label_printed_at")
    op.drop_column("return_intake_rows", "label_print_status")
    op.drop_column("return_intake_rows", "label_print_required")
    op.drop_column("return_intake_rows", "return_label_no")
    op.drop_column("return_intake_rows", "return_management_no")
    op.drop_column("return_intake_rows", "judged_by")
    op.drop_column("return_intake_rows", "judged_at")
    op.drop_column("return_intake_rows", "judgement_memo")
    op.drop_column("return_intake_rows", "judgement_status")
