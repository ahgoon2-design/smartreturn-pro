"""Add channel candidate corrections.

Revision ID: 0a1b2c3d4e5f
Revises: f0a1b2c3d456
Create Date: 2026-06-09
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0a1b2c3d4e5f"
down_revision: str | Sequence[str] | None = "f0a1b2c3d456"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("channel_return_candidates", sa.Column("manual_client_unit_id", sa.Integer(), nullable=True))
    op.add_column("channel_return_candidates", sa.Column("manual_product_id", sa.Integer(), nullable=True))
    op.add_column("channel_return_candidates", sa.Column("manual_product_code", sa.String(length=80), nullable=True))
    op.add_column("channel_return_candidates", sa.Column("manual_return_tracking_no", sa.String(length=100), nullable=True))
    op.add_column("channel_return_candidates", sa.Column("manual_original_tracking_no", sa.String(length=100), nullable=True))
    op.add_column("channel_return_candidates", sa.Column("manual_qty", sa.Integer(), nullable=True))
    op.add_column("channel_return_candidates", sa.Column("manual_review_note", sa.Text(), nullable=True))
    op.add_column("channel_return_candidates", sa.Column("manual_reviewed_by", sa.Integer(), nullable=True))
    op.add_column("channel_return_candidates", sa.Column("manual_reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "channel_return_candidates",
        sa.Column("correction_status", sa.String(length=50), server_default="NONE", nullable=False),
    )
    op.add_column(
        "channel_return_candidates",
        sa.Column("correction_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_foreign_key(
        "fk_channel_return_candidates_manual_client_unit_id",
        "channel_return_candidates",
        "client_units",
        ["manual_client_unit_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_channel_return_candidates_manual_product_id",
        "channel_return_candidates",
        "products",
        ["manual_product_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_channel_return_candidates_manual_reviewed_by",
        "channel_return_candidates",
        "users",
        ["manual_reviewed_by"],
        ["id"],
    )

    op.create_table(
        "product_channel_mappings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("client_unit_id", sa.Integer(), nullable=True),
        sa.Column("channel_type", sa.String(length=80), nullable=False),
        sa.Column("channel_account_id", sa.Integer(), nullable=True),
        sa.Column("external_product_id", sa.String(length=255), nullable=True),
        sa.Column("external_seller_product_code", sa.String(length=255), nullable=True),
        sa.Column("external_product_name_norm", sa.String(length=255), nullable=True),
        sa.Column("external_option_name_norm", sa.String(length=255), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("product_code", sa.String(length=80), nullable=False),
        sa.Column("decision_type", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Integer(), server_default="100", nullable=False),
        sa.Column("created_from_candidate_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["channel_account_id"], ["channel_accounts.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["client_unit_id"], ["client_units.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_from_candidate_id"], ["channel_return_candidates.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_product_channel_mappings_lookup",
        "product_channel_mappings",
        [
            "client_id",
            "channel_type",
            "external_seller_product_code",
            "external_product_name_norm",
            "external_option_name_norm",
        ],
        unique=False,
    )
    op.create_index(
        "ix_product_channel_mappings_product",
        "product_channel_mappings",
        ["client_id", "product_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_product_channel_mappings_product", table_name="product_channel_mappings")
    op.drop_index("ix_product_channel_mappings_lookup", table_name="product_channel_mappings")
    op.drop_table("product_channel_mappings")
    op.drop_constraint(
        "fk_channel_return_candidates_manual_reviewed_by",
        "channel_return_candidates",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_channel_return_candidates_manual_product_id",
        "channel_return_candidates",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_channel_return_candidates_manual_client_unit_id",
        "channel_return_candidates",
        type_="foreignkey",
    )
    op.drop_column("channel_return_candidates", "correction_json")
    op.drop_column("channel_return_candidates", "correction_status")
    op.drop_column("channel_return_candidates", "manual_reviewed_at")
    op.drop_column("channel_return_candidates", "manual_reviewed_by")
    op.drop_column("channel_return_candidates", "manual_review_note")
    op.drop_column("channel_return_candidates", "manual_qty")
    op.drop_column("channel_return_candidates", "manual_original_tracking_no")
    op.drop_column("channel_return_candidates", "manual_return_tracking_no")
    op.drop_column("channel_return_candidates", "manual_product_code")
    op.drop_column("channel_return_candidates", "manual_product_id")
    op.drop_column("channel_return_candidates", "manual_client_unit_id")
