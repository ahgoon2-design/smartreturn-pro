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
