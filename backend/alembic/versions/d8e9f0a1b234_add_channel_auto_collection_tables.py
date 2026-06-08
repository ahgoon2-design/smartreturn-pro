"""Add channel auto collection tables.

Revision ID: d8e9f0a1b234
Revises: c7d8e9f0a123
Create Date: 2026-06-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d8e9f0a1b234"
down_revision: str | Sequence[str] | None = "c7d8e9f0a123"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "channel_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("client_unit_id", sa.Integer(), nullable=True),
        sa.Column("channel_type", sa.String(length=80), nullable=False),
        sa.Column("account_name", sa.String(length=255), nullable=False),
        sa.Column("store_name", sa.String(length=255), nullable=False),
        sa.Column("external_account_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="AUTH_REQUIRED", nullable=False),
        sa.Column("auth_status", sa.String(length=50), server_default="NOT_CONNECTED", nullable=False),
        sa.Column("credential_ref", sa.String(length=255), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=100), nullable=True),
        sa.Column("last_error_message", sa.String(length=500), nullable=True),
        sa.Column("sync_enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["client_unit_id"], ["client_units.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", "channel_type", "external_account_id", name="uq_channel_accounts_external"),
    )
    op.create_index("ix_channel_accounts_client_channel", "channel_accounts", ["client_id", "channel_type"], unique=False)
    op.create_index("ix_channel_accounts_status", "channel_accounts", ["status", "auth_status"], unique=False)
    op.create_index("ix_channel_accounts_sync_enabled", "channel_accounts", ["sync_enabled"], unique=False)

    op.create_table(
        "channel_sync_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("channel_account_id", sa.Integer(), nullable=False),
        sa.Column("job_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="PENDING", nullable=False),
        sa.Column("cursor_from", sa.String(length=255), nullable=True),
        sa.Column("cursor_to", sa.String(length=255), nullable=True),
        sa.Column("cursor_more_from", sa.String(length=255), nullable=True),
        sa.Column("cursor_more_sequence", sa.String(length=255), nullable=True),
        sa.Column("total_collected", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_inserted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_updated", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_skipped", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_failed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["channel_account_id"], ["channel_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_channel_sync_jobs_account_created", "channel_sync_jobs", ["channel_account_id", "created_at"], unique=False)
    op.create_index("ix_channel_sync_jobs_status", "channel_sync_jobs", ["status"], unique=False)
    op.create_index("ix_channel_sync_jobs_job_type", "channel_sync_jobs", ["job_type"], unique=False)

    op.create_table(
        "channel_raw_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("channel_account_id", sa.Integer(), nullable=False),
        sa.Column("channel_type", sa.String(length=80), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("external_order_id", sa.String(length=255), nullable=True),
        sa.Column("external_product_order_id", sa.String(length=255), nullable=True),
        sa.Column("external_claim_id", sa.String(length=255), nullable=True),
        sa.Column("external_tracking_no_hash", sa.String(length=128), nullable=True),
        sa.Column("last_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_hash", sa.String(length=128), nullable=False),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("process_status", sa.String(length=50), server_default="RECEIVED", nullable=False),
        sa.Column("process_error_code", sa.String(length=100), nullable=True),
        sa.Column("process_error_message", sa.String(length=500), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["channel_account_id"], ["channel_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_account_id", "raw_hash", name="uq_channel_raw_events_account_hash"),
    )
    op.create_index("ix_channel_raw_events_account_status", "channel_raw_events", ["channel_account_id", "process_status"], unique=False)
    op.create_index(
        "ix_channel_raw_events_external_claim",
        "channel_raw_events",
        ["channel_account_id", "external_product_order_id", "external_claim_id"],
        unique=False,
    )
    op.create_index("ix_channel_raw_events_channel_type", "channel_raw_events", ["channel_type"], unique=False)
    op.create_index("ix_channel_raw_events_collected_at", "channel_raw_events", ["collected_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_channel_raw_events_collected_at", table_name="channel_raw_events")
    op.drop_index("ix_channel_raw_events_channel_type", table_name="channel_raw_events")
    op.drop_index("ix_channel_raw_events_external_claim", table_name="channel_raw_events")
    op.drop_index("ix_channel_raw_events_account_status", table_name="channel_raw_events")
    op.drop_table("channel_raw_events")
    op.drop_index("ix_channel_sync_jobs_job_type", table_name="channel_sync_jobs")
    op.drop_index("ix_channel_sync_jobs_status", table_name="channel_sync_jobs")
    op.drop_index("ix_channel_sync_jobs_account_created", table_name="channel_sync_jobs")
    op.drop_table("channel_sync_jobs")
    op.drop_index("ix_channel_accounts_sync_enabled", table_name="channel_accounts")
    op.drop_index("ix_channel_accounts_status", table_name="channel_accounts")
    op.drop_index("ix_channel_accounts_client_channel", table_name="channel_accounts")
    op.drop_table("channel_accounts")
