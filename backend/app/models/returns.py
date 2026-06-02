from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReturnIntakeBatch(Base):
    __tablename__ = "return_intake_batches"
    __table_args__ = (
        Index("ix_return_intake_batches_client_created", "client_id", "created_at"),
        Index("ix_return_intake_batches_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    warning_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    memo: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ReturnIntakeRow(Base):
    __tablename__ = "return_intake_rows"
    __table_args__ = (
        UniqueConstraint("batch_id", "row_no", name="uq_return_intake_rows_batch_row_no"),
        Index("ix_return_intake_rows_batch_row_no", "batch_id", "row_no"),
        Index("ix_return_intake_rows_batch_validation", "batch_id", "validation_status"),
        Index("ix_return_intake_rows_client_status", "client_id", "status"),
        Index("ix_return_intake_rows_client_judgement", "client_id", "judgement_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("return_intake_batches.id"), nullable=False)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    row_no: Mapped[int] = mapped_column(Integer, nullable=False)
    order_no: Mapped[str | None] = mapped_column(String(100))
    return_tracking_no: Mapped[str | None] = mapped_column(String(100))
    original_tracking_no: Mapped[str | None] = mapped_column(String(100))
    product_code: Mapped[str | None] = mapped_column(String(80))
    barcode: Mapped[str | None] = mapped_column(String(100))
    product_name: Mapped[str | None] = mapped_column(String(255))
    option_name: Mapped[str | None] = mapped_column(String(255))
    qty: Mapped[int | None] = mapped_column(Integer)
    return_reason: Mapped[str | None] = mapped_column(String(255))
    customer_name: Mapped[str | None] = mapped_column(String(100))
    customer_phone_masked: Mapped[str | None] = mapped_column(String(50))
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(50), nullable=False, default="NOT_VALIDATED")
    validation_message: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="RECEIVED")
    judgement_status: Mapped[str | None] = mapped_column(String(50))
    judgement_memo: Mapped[str | None] = mapped_column(Text)
    judged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    judged_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    return_management_no: Mapped[str | None] = mapped_column(String(80))
    return_label_no: Mapped[str | None] = mapped_column(String(80))
    label_print_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    label_print_status: Mapped[str | None] = mapped_column(String(50))
    label_printed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
