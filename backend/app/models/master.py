from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Agency(Base):
    __tablename__ = "agencies"
    __table_args__ = (
        Index("ix_agencies_active_yn", "active_yn"),
        Index("ix_agencies_agency_name", "agency_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agency_code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    agency_name: Mapped[str] = mapped_column(String(255), nullable=False)
    agency_type: Mapped[str | None] = mapped_column(String(80))
    active_yn: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Client(Base):
    __tablename__ = "clients"
    __table_args__ = (
        Index("ix_clients_agency_id", "agency_id"),
        Index("ix_clients_active_yn", "active_yn"),
        Index("ix_clients_client_name", "client_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agency_id: Mapped[int | None] = mapped_column(ForeignKey("agencies.id"))
    client_code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_no: Mapped[str | None] = mapped_column(String(50))
    contact_name: Mapped[str | None] = mapped_column(String(100))
    contact_phone: Mapped[str | None] = mapped_column(String(50))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    use_oms: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    use_wms: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    use_returns: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    use_settlement: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    active_yn: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Warehouse(Base):
    __tablename__ = "warehouses"
    __table_args__ = (
        Index("ix_warehouses_active_yn", "active_yn"),
        Index("ix_warehouses_warehouse_type", "warehouse_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    warehouse_code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    warehouse_name: Mapped[str] = mapped_column(String(255), nullable=False)
    warehouse_type: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(String(500))
    active_yn: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ClientWarehouseSetting(Base):
    __tablename__ = "client_warehouse_settings"
    __table_args__ = (
        UniqueConstraint("client_id", "warehouse_id", "usage_type", name="uq_client_warehouse_usage"),
        Index("ix_client_warehouse_settings_client_id", "client_id"),
        Index("ix_client_warehouse_settings_warehouse_id", "warehouse_id"),
        Index("ix_client_warehouse_settings_client_usage", "client_id", "usage_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    usage_type: Mapped[str] = mapped_column(String(80), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    active_yn: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ClientUnit(Base):
    __tablename__ = "client_units"
    __table_args__ = (
        UniqueConstraint("client_id", "unit_code", name="uq_client_units_client_unit_code"),
        Index("ix_client_units_client_active", "client_id", "active_yn"),
        Index("ix_client_units_default_warehouse", "default_warehouse_id"),
        Index("ix_client_units_return_warehouse", "return_warehouse_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    unit_code: Mapped[str] = mapped_column(String(80), nullable=False)
    unit_name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_type: Mapped[str | None] = mapped_column(String(50))
    default_warehouse_id: Mapped[int | None] = mapped_column(ForeignKey("warehouses.id"))
    return_warehouse_id: Mapped[int | None] = mapped_column(ForeignKey("warehouses.id"))
    active_yn: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    memo: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ReturnJudgmentWarehouseRoute(Base):
    __tablename__ = "return_judgment_warehouse_routes"
    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "client_unit_id",
            "judgment_code",
            "warehouse_id",
            name="uq_return_judgment_warehouse_route",
        ),
        Index("ix_return_judgment_routes_client_judgment", "client_id", "judgment_code", "active_yn"),
        Index("ix_return_judgment_routes_client_unit", "client_id", "client_unit_id", "active_yn"),
        Index("ix_return_judgment_routes_warehouse", "warehouse_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    client_unit_id: Mapped[int | None] = mapped_column(ForeignKey("client_units.id"))
    judgment_code: Mapped[str] = mapped_column(String(80), nullable=False)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    active_yn: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    memo: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "location_code", name="uq_locations_warehouse_code"),
        Index("ix_locations_warehouse_id", "warehouse_id"),
        Index("ix_locations_active_yn", "active_yn"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    location_code: Mapped[str] = mapped_column(String(80), nullable=False)
    location_name: Mapped[str] = mapped_column(String(255), nullable=False)
    location_type: Mapped[str | None] = mapped_column(String(50))
    active_yn: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("client_id", "product_code", name="uq_products_client_product_code"),
        Index("ix_products_client_product_name", "client_id", "product_name"),
        Index("ix_products_client_barcode", "client_id", "barcode"),
        Index("ix_products_client_active", "client_id", "active_yn"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    product_code: Mapped[str] = mapped_column(String(80), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(100))
    specification: Mapped[str | None] = mapped_column(String(255))
    unit_name: Mapped[str | None] = mapped_column(String(50))
    active_yn: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ProductBarcode(Base):
    __tablename__ = "product_barcodes"
    __table_args__ = (
        UniqueConstraint("client_id", "barcode_norm", name="uq_product_barcodes_client_barcode_norm"),
        CheckConstraint("unit_qty >= 1", name="ck_product_barcodes_unit_qty_positive"),
        Index("ix_product_barcodes_client_product", "client_id", "product_id"),
        Index("ix_product_barcodes_client_type", "client_id", "barcode_type"),
        Index("ix_product_barcodes_client_active", "client_id", "active_yn"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    barcode: Mapped[str] = mapped_column(String(100), nullable=False)
    barcode_norm: Mapped[str] = mapped_column(String(100), nullable=False)
    barcode_type: Mapped[str] = mapped_column(String(50), nullable=False)
    unit_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    active_yn: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class CommonCodeGroup(Base):
    __tablename__ = "common_code_groups"
    __table_args__ = (Index("ix_common_code_groups_active_yn", "active_yn"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    group_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    active_yn: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class CommonCode(Base):
    __tablename__ = "common_codes"
    __table_args__ = (
        UniqueConstraint("group_id", "code_value", name="uq_common_codes_group_value"),
        Index("ix_common_codes_group_active", "group_id", "active_yn"),
        Index("ix_common_codes_sort_order", "sort_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("common_code_groups.id"), nullable=False)
    code_value: Mapped[str] = mapped_column(String(80), nullable=False)
    code_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    system_yn: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    locked_yn: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    active_yn: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
