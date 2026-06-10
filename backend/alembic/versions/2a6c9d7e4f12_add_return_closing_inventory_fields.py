"""add return closing inventory fields

Revision ID: 2a6c9d7e4f12
Revises: 8f4a2b6d9c10
Create Date: 2026-06-04 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "2a6c9d7e4f12"
down_revision: str | Sequence[str] | None = "8f4a2b6d9c10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "return_intake_rows",
        sa.Column(
            "inventory_reflected_yn",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "return_intake_rows",
        sa.Column("inventory_reflected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "return_intake_rows",
        sa.Column("inventory_event_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_return_intake_rows_inventory_event_id",
        "return_intake_rows",
        "inventory_events",
        ["inventory_event_id"],
        ["id"],
    )
    op.create_index(
        "ix_return_intake_rows_closing_candidates",
        "return_intake_rows",
        ["client_id", "status", "judgement_status", "inventory_reflected_yn"],
        unique=False,
    )
    op.create_index(
        "ix_return_intake_rows_inventory_event_id",
        "return_intake_rows",
        ["inventory_event_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_return_intake_rows_inventory_event_id", table_name="return_intake_rows")
    op.drop_index("ix_return_intake_rows_closing_candidates", table_name="return_intake_rows")
    op.drop_constraint("fk_return_intake_rows_inventory_event_id", "return_intake_rows", type_="foreignkey")
    op.drop_column("return_intake_rows", "inventory_event_id")
    op.drop_column("return_intake_rows", "inventory_reflected_at")
    op.drop_column("return_intake_rows", "inventory_reflected_yn")
