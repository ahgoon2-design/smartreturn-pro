"""Add channel return candidates.

Revision ID: e9f0a1b2c345
Revises: d8e9f0a1b234
Create Date: 2026-06-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e9f0a1b2c345"
down_revision: str | Sequence[str] | None = "d8e9f0a1b234"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "channel_return_candidates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("channel_raw_event_id", sa.Integer(), nullable=False),
        sa.Column("channel_account_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("client_unit_id", sa.Integer(), nullable=True),
        sa.Column("source_type", sa.String(length=80), server_default="CHANNEL_API", nullable=False),
        sa.Column("source_origin", sa.String(length=80), nullable=False),
        sa.Column("external_order_id", sa.String(length=255), nullable=True),
        sa.Column("external_product_order_id", sa.String(length=255), nullable=True),
        sa.Column("external_claim_id", sa.String(length=255), nullable=True),
        sa.Column("return_tracking_no", sa.String(length=100), nullable=True),
        sa.Column("original_tracking_no", sa.String(length=100), nullable=True),
        sa.Column("tracking_no_for_scan", sa.String(length=100), nullable=True),
        sa.Column("product_code", sa.String(length=80), nullable=True),
        sa.Column("barcode", sa.String(length=100), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("product_name", sa.String(length=255), nullable=True),
        sa.Column("option_name", sa.String(length=255), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=True),
        sa.Column("claim_reason", sa.String(length=255), nullable=True),
        sa.Column("claim_status", sa.String(length=80), nullable=True),
        sa.Column("canonical_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("match_status", sa.String(length=50), nullable=False),
        sa.Column("match_reason", sa.Text(), nullable=False),
        sa.Column("risk_flags_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["channel_account_id"], ["channel_accounts.id"]),
        sa.ForeignKeyConstraint(["channel_raw_event_id"], ["channel_raw_events.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["client_unit_id"], ["client_units.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_raw_event_id", name="uq_channel_return_candidates_raw_event"),
    )
    op.create_index(
        "ix_channel_return_candidates_account_status",
        "channel_return_candidates",
        ["channel_account_id", "match_status"],
        unique=False,
    )
    op.create_index(
        "ix_channel_return_candidates_client_status",
        "channel_return_candidates",
        ["client_id", "match_status"],
        unique=False,
    )
    op.create_index(
        "ix_channel_return_candidates_external_claim",
        "channel_return_candidates",
        ["client_id", "external_product_order_id", "external_claim_id"],
        unique=False,
    )
    op.create_index(
        "ix_channel_return_candidates_return_tracking",
        "channel_return_candidates",
        ["client_id", "return_tracking_no"],
        unique=False,
    )
    op.create_index(
        "ix_channel_return_candidates_scan_tracking",
        "channel_return_candidates",
        ["client_id", "tracking_no_for_scan"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_channel_return_candidates_scan_tracking", table_name="channel_return_candidates")
    op.drop_index("ix_channel_return_candidates_return_tracking", table_name="channel_return_candidates")
    op.drop_index("ix_channel_return_candidates_external_claim", table_name="channel_return_candidates")
    op.drop_index("ix_channel_return_candidates_client_status", table_name="channel_return_candidates")
    op.drop_index("ix_channel_return_candidates_account_status", table_name="channel_return_candidates")
    op.drop_table("channel_return_candidates")
