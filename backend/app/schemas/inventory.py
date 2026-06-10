from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CurrentInventoryItemResponse(BaseModel):
    inventory_id: int
    client_id: int
    client_code: str | None = None
    client_name: str | None = None
    warehouse_id: int
    warehouse_code: str | None = None
    warehouse_name: str | None = None
    product_id: int
    product_code: str | None = None
    product_name: str | None = None
    barcode: str | None = None
    stock_status: str
    qty: int
    updated_at: datetime


class CurrentInventoryListResponse(BaseModel):
    items: list[CurrentInventoryItemResponse]
    total_count: int
    page: int
    page_size: int


class InventoryEventItemResponse(BaseModel):
    event_id: int
    event_no: str
    client_id: int
    client_code: str | None = None
    client_name: str | None = None
    warehouse_id: int
    warehouse_code: str | None = None
    warehouse_name: str | None = None
    product_id: int
    product_code: str | None = None
    product_name: str | None = None
    barcode: str | None = None
    event_type: str
    source_type: str
    source_id: int
    source_line_id: int | None = None
    stock_status: str
    qty: int
    idempotency_key: str
    event_reason: str | None = None
    memo: str | None = None
    created_at: datetime
    created_by: int | None = None


class InventoryEventListResponse(BaseModel):
    items: list[InventoryEventItemResponse]
    total_count: int
    page: int
    page_size: int
