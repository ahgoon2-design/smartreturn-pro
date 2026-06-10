"""Manage product channel mapping status.

Revision ID: 1b2c3d4e5f60
Revises: 0a1b2c3d4e5f
Create Date: 2026-06-09
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "1b2c3d4e5f60"
down_revision: str | Sequence[str] | None = "0a1b2c3d4e5f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("product_channel_mappings", sa.Column("product_name", sa.String(length=255), nullable=True))
    op.add_column(
        "product_channel_mappings",
        sa.Column("status", sa.String(length=50), server_default="ACTIVE", nullable=False),
    )
    op.add_column("product_channel_mappings", sa.Column("conflict_group_key", sa.String(length=500), nullable=True))
    op.add_column("product_channel_mappings", sa.Column("conflict_reason", sa.String(length=500), nullable=True))
    op.add_column("product_channel_mappings", sa.Column("approved_by", sa.Integer(), nullable=True))
    op.add_column("product_channel_mappings", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("product_channel_mappings", sa.Column("rejected_by", sa.Integer(), nullable=True))
    op.add_column("product_channel_mappings", sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("product_channel_mappings", sa.Column("disabled_by", sa.Integer(), nullable=True))
    op.add_column("product_channel_mappings", sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("product_channel_mappings", sa.Column("note", sa.Text(), nullable=True))
    op.add_column("product_channel_mappings", sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "product_channel_mappings",
        sa.Column("used_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_foreign_key(
        "fk_product_channel_mappings_approved_by",
        "product_channel_mappings",
        "users",
        ["approved_by"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_product_channel_mappings_rejected_by",
        "product_channel_mappings",
        "users",
        ["rejected_by"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_product_channel_mappings_disabled_by",
        "product_channel_mappings",
        "users",
        ["disabled_by"],
        ["id"],
    )
    op.create_index(
        "ix_product_channel_mappings_status",
        "product_channel_mappings",
        ["client_id", "channel_type", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_product_channel_mappings_status", table_name="product_channel_mappings")
    op.drop_constraint("fk_product_channel_mappings_disabled_by", "product_channel_mappings", type_="foreignkey")
    op.drop_constraint("fk_product_channel_mappings_rejected_by", "product_channel_mappings", type_="foreignkey")
    op.drop_constraint("fk_product_channel_mappings_approved_by", "product_channel_mappings", type_="foreignkey")
    op.drop_column("product_channel_mappings", "used_count")
    op.drop_column("product_channel_mappings", "last_used_at")
    op.drop_column("product_channel_mappings", "note")
    op.drop_column("product_channel_mappings", "disabled_at")
    op.drop_column("product_channel_mappings", "disabled_by")
    op.drop_column("product_channel_mappings", "rejected_at")
    op.drop_column("product_channel_mappings", "rejected_by")
    op.drop_column("product_channel_mappings", "approved_at")
    op.drop_column("product_channel_mappings", "approved_by")
    op.drop_column("product_channel_mappings", "conflict_reason")
    op.drop_column("product_channel_mappings", "conflict_group_key")
    op.drop_column("product_channel_mappings", "status")
    op.drop_column("product_channel_mappings", "product_name")
