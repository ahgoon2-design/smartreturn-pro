from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChannelAccount(Base):
    __tablename__ = "channel_accounts"
    __table_args__ = (
        UniqueConstraint("client_id", "channel_type", "external_account_id", name="uq_channel_accounts_external"),
        Index("ix_channel_accounts_client_channel", "client_id", "channel_type"),
        Index("ix_channel_accounts_status", "status", "auth_status"),
        Index("ix_channel_accounts_sync_enabled", "sync_enabled"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    client_unit_id: Mapped[int | None] = mapped_column(ForeignKey("client_units.id"))
    channel_type: Mapped[str] = mapped_column(String(80), nullable=False)
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    store_name: Mapped[str] = mapped_column(String(255), nullable=False)
    external_account_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="AUTH_REQUIRED", server_default="AUTH_REQUIRED")
    auth_status: Mapped[str] = mapped_column(String(50), nullable=False, default="NOT_CONNECTED", server_default="NOT_CONNECTED")
    credential_ref: Mapped[str | None] = mapped_column(String(255))
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(100))
    last_error_message: Mapped[str | None] = mapped_column(String(500))
    sync_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ChannelSyncJob(Base):
    __tablename__ = "channel_sync_jobs"
    __table_args__ = (
        Index("ix_channel_sync_jobs_account_created", "channel_account_id", "created_at"),
        Index("ix_channel_sync_jobs_status", "status"),
        Index("ix_channel_sync_jobs_job_type", "job_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_account_id: Mapped[int] = mapped_column(ForeignKey("channel_accounts.id"), nullable=False)
    job_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING", server_default="PENDING")
    cursor_from: Mapped[str | None] = mapped_column(String(255))
    cursor_to: Mapped[str | None] = mapped_column(String(255))
    cursor_more_from: Mapped[str | None] = mapped_column(String(255))
    cursor_more_sequence: Mapped[str | None] = mapped_column(String(255))
    total_collected: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ChannelRawEvent(Base):
    __tablename__ = "channel_raw_events"
    __table_args__ = (
        UniqueConstraint("channel_account_id", "raw_hash", name="uq_channel_raw_events_account_hash"),
        Index("ix_channel_raw_events_account_status", "channel_account_id", "process_status"),
        Index("ix_channel_raw_events_external_claim", "channel_account_id", "external_product_order_id", "external_claim_id"),
        Index("ix_channel_raw_events_channel_type", "channel_type"),
        Index("ix_channel_raw_events_collected_at", "collected_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_account_id: Mapped[int] = mapped_column(ForeignKey("channel_accounts.id"), nullable=False)
    channel_type: Mapped[str] = mapped_column(String(80), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    external_order_id: Mapped[str | None] = mapped_column(String(255))
    external_product_order_id: Mapped[str | None] = mapped_column(String(255))
    external_claim_id: Mapped[str | None] = mapped_column(String(255))
    external_tracking_no_hash: Mapped[str | None] = mapped_column(String(128))
    last_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    raw_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    process_status: Mapped[str] = mapped_column(String(50), nullable=False, default="RECEIVED", server_default="RECEIVED")
    process_error_code: Mapped[str | None] = mapped_column(String(100))
    process_error_message: Mapped[str | None] = mapped_column(String(500))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ChannelReturnCandidate(Base):
    __tablename__ = "channel_return_candidates"
    __table_args__ = (
        UniqueConstraint("channel_raw_event_id", name="uq_channel_return_candidates_raw_event"),
        Index("ix_channel_return_candidates_account_status", "channel_account_id", "match_status"),
        Index("ix_channel_return_candidates_client_status", "client_id", "match_status"),
        Index("ix_channel_return_candidates_external_claim", "client_id", "external_product_order_id", "external_claim_id"),
        Index("ix_channel_return_candidates_return_tracking", "client_id", "return_tracking_no"),
        Index("ix_channel_return_candidates_scan_tracking", "client_id", "tracking_no_for_scan"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_raw_event_id: Mapped[int] = mapped_column(ForeignKey("channel_raw_events.id"), nullable=False)
    channel_account_id: Mapped[int] = mapped_column(ForeignKey("channel_accounts.id"), nullable=False)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    client_unit_id: Mapped[int | None] = mapped_column(ForeignKey("client_units.id"))
    source_type: Mapped[str] = mapped_column(String(80), nullable=False, default="CHANNEL_API", server_default="CHANNEL_API")
    source_origin: Mapped[str] = mapped_column(String(80), nullable=False)
    external_order_id: Mapped[str | None] = mapped_column(String(255))
    external_product_order_id: Mapped[str | None] = mapped_column(String(255))
    external_claim_id: Mapped[str | None] = mapped_column(String(255))
    return_tracking_no: Mapped[str | None] = mapped_column(String(100))
    original_tracking_no: Mapped[str | None] = mapped_column(String(100))
    tracking_no_for_scan: Mapped[str | None] = mapped_column(String(100))
    product_code: Mapped[str | None] = mapped_column(String(80))
    barcode: Mapped[str | None] = mapped_column(String(100))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    product_name: Mapped[str | None] = mapped_column(String(255))
    option_name: Mapped[str | None] = mapped_column(String(255))
    qty: Mapped[int | None] = mapped_column(Integer)
    claim_reason: Mapped[str | None] = mapped_column(String(255))
    claim_status: Mapped[str | None] = mapped_column(String(80))
    canonical_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    match_status: Mapped[str] = mapped_column(String(50), nullable=False)
    match_reason: Mapped[str] = mapped_column(Text, nullable=False)
    risk_flags_json: Mapped[list | None] = mapped_column(JSONB)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    return_expected_id: Mapped[int | None] = mapped_column(ForeignKey("return_intake_rows.id"))
    return_expected_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    return_expected_create_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="NOT_CREATED",
        server_default="NOT_CREATED",
    )
    return_expected_create_error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
