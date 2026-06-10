from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InventoryEvent(Base):
    __tablename__ = "inventory_events"
    __table_args__ = (
        UniqueConstraint("event_no", name="uq_inventory_events_event_no"),
        UniqueConstraint("idempotency_key", name="uq_inventory_events_idempotency_key"),
        Index("ix_inventory_events_agency_client_created", "agency_id", "client_id", "created_at"),
        Index("ix_inventory_events_client_product_created", "client_id", "product_id", "created_at"),
        Index("ix_inventory_events_source", "source_type", "source_id"),
        Index("ix_inventory_events_reverse_event_id", "reverse_event_id"),
        Index("ix_inventory_events_stock_scope", "client_id", "warehouse_id", "product_id", "stock_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_no: Mapped[str] = mapped_column(String(80), nullable=False)
    agency_id: Mapped[int | None] = mapped_column(ForeignKey("agencies.id"))
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    product_code: Mapped[str | None] = mapped_column(String(80))
    stock_status: Mapped[str] = mapped_column(String(50), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    qty_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    source_line_id: Mapped[int | None] = mapped_column(Integer)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    reverse_event_id: Mapped[int | None] = mapped_column(ForeignKey("inventory_events.id"))
    event_reason: Mapped[str | None] = mapped_column(String(255))
    memo: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    raw_json: Mapped[dict | None] = mapped_column(JSONB)


class CurrentInventory(Base):
    __tablename__ = "current_inventory"
    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "warehouse_id",
            "location_id",
            "product_id",
            "stock_status",
            name="uq_current_inventory_scope",
        ),
        Index("ix_current_inventory_agency_scope", "agency_id", "client_id", "warehouse_id", "product_id"),
        Index("ix_current_inventory_client_product", "client_id", "product_id"),
        Index("ix_current_inventory_warehouse_product", "warehouse_id", "product_id"),
        Index("ix_current_inventory_stock_scope", "client_id", "warehouse_id", "product_id", "stock_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agency_id: Mapped[int | None] = mapped_column(ForeignKey("agencies.id"))
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    stock_status: Mapped[str] = mapped_column(String(50), nullable=False)
    qty_on_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
