"""add return external outbound fields

Revision ID: 3b7d2e9f4a61
Revises: 2a6c9d7e4f12
Create Date: 2026-06-05 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "3b7d2e9f4a61"
down_revision: str | Sequence[str] | None = "2a6c9d7e4f12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "return_intake_rows",
        sa.Column(
            "external_outbound_required",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "return_intake_rows",
        sa.Column(
            "external_outbound_status",
            sa.String(length=50),
            server_default="NOT_REQUIRED",
            nullable=False,
        ),
    )
    op.add_column(
        "return_intake_rows",
        sa.Column("external_outbound_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "return_intake_rows",
        sa.Column("external_outbound_confirmed_by", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_return_intake_rows_external_outbound_confirmed_by",
        "return_intake_rows",
        "users",
        ["external_outbound_confirmed_by"],
        ["id"],
    )
    op.create_index(
        "ix_return_intake_rows_external_outbound",
        "return_intake_rows",
        ["client_id", "external_outbound_status", "judgement_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_return_intake_rows_external_outbound", table_name="return_intake_rows")
    op.drop_constraint(
        "fk_return_intake_rows_external_outbound_confirmed_by",
        "return_intake_rows",
        type_="foreignkey",
    )
    op.drop_column("return_intake_rows", "external_outbound_confirmed_by")
    op.drop_column("return_intake_rows", "external_outbound_at")
    op.drop_column("return_intake_rows", "external_outbound_status")
    op.drop_column("return_intake_rows", "external_outbound_required")
