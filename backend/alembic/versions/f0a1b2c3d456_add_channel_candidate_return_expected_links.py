"""Add channel candidate return expected links.

Revision ID: f0a1b2c3d456
Revises: e9f0a1b2c345
Create Date: 2026-06-09
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f0a1b2c3d456"
down_revision: str | Sequence[str] | None = "e9f0a1b2c345"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("channel_return_candidates", sa.Column("return_expected_id", sa.Integer(), nullable=True))
    op.add_column(
        "channel_return_candidates",
        sa.Column("return_expected_created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "channel_return_candidates",
        sa.Column(
            "return_expected_create_status",
            sa.String(length=50),
            server_default="NOT_CREATED",
            nullable=False,
        ),
    )
    op.add_column(
        "channel_return_candidates",
        sa.Column("return_expected_create_error", sa.String(length=500), nullable=True),
    )
    op.create_foreign_key(
        "fk_channel_return_candidates_return_expected_id",
        "channel_return_candidates",
        "return_intake_rows",
        ["return_expected_id"],
        ["id"],
    )
    op.create_index(
        "ix_channel_return_candidates_expected_status",
        "channel_return_candidates",
        ["return_expected_create_status", "return_expected_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_channel_return_candidates_expected_status", table_name="channel_return_candidates")
    op.drop_constraint(
        "fk_channel_return_candidates_return_expected_id",
        "channel_return_candidates",
        type_="foreignkey",
    )
    op.drop_column("channel_return_candidates", "return_expected_create_error")
    op.drop_column("channel_return_candidates", "return_expected_create_status")
    op.drop_column("channel_return_candidates", "return_expected_created_at")
    op.drop_column("channel_return_candidates", "return_expected_id")
