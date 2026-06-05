from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.auth_context import resolve_effective_client_id
from app.core.permissions import require_permission
from app.repositories import inventory_repository
from app.schemas.auth import AuthContext
from datetime import datetime

from app.schemas.inventory import (
    CurrentInventoryItemResponse,
    CurrentInventoryListResponse,
    InventoryEventItemResponse,
    InventoryEventListResponse,
)


def list_current_inventory(
    db: Session,
    auth: AuthContext,
    *,
    client_id: int | None = None,
    warehouse_id: int | None = None,
    product_code: str | None = None,
    barcode: str | None = None,
    keyword: str | None = None,
    stock_status: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict:
    require_permission(auth, "INVENTORY_VIEW")
    effective_client_id = resolve_effective_client_id(auth, client_id, allow_all_clients=True)
    rows, total_count = inventory_repository.list_current_inventory(
        db,
        client_id=effective_client_id,
        warehouse_id=warehouse_id,
        product_code=_clean(product_code),
        barcode=_clean(barcode),
        keyword=_clean(keyword),
        stock_status=_clean(stock_status),
        page=page,
        page_size=page_size,
    )
    response = CurrentInventoryListResponse(
        items=[
            CurrentInventoryItemResponse(
                inventory_id=current.id,
                client_id=current.client_id,
                client_code=client.client_code,
                client_name=client.client_name,
                warehouse_id=current.warehouse_id,
                warehouse_code=warehouse.warehouse_code,
                warehouse_name=warehouse.warehouse_name,
                product_id=current.product_id,
                product_code=product.product_code,
                product_name=product.product_name,
                barcode=product.barcode,
                stock_status=current.stock_status,
                qty=current.qty_on_hand,
                updated_at=current.updated_at,
            )
            for current, client, warehouse, product in rows
        ],
        total_count=total_count,
        page=page,
        page_size=page_size,
    )
    return response.model_dump()


def list_inventory_events(
    db: Session,
    auth: AuthContext,
    *,
    client_id: int | None = None,
    warehouse_id: int | None = None,
    product_code: str | None = None,
    barcode: str | None = None,
    keyword: str | None = None,
    event_type: str | None = None,
    source_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict:
    require_permission(auth, "INVENTORY_VIEW")
    effective_client_id = resolve_effective_client_id(auth, client_id, allow_all_clients=True)
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 500)
    rows, total_count = inventory_repository.list_inventory_events(
        db,
        client_id=effective_client_id,
        warehouse_id=warehouse_id,
        product_code=_clean(product_code),
        barcode=_clean(barcode),
        keyword=_clean(keyword),
        event_type=_clean(event_type),
        source_type=_clean(source_type),
        date_from=date_from,
        date_to=date_to,
        page=safe_page,
        page_size=safe_page_size,
    )
    response = InventoryEventListResponse(
        items=[
            InventoryEventItemResponse(
                event_id=event.id,
                event_no=event.event_no,
                client_id=event.client_id,
                client_code=client.client_code,
                client_name=client.client_name,
                warehouse_id=event.warehouse_id,
                warehouse_code=warehouse.warehouse_code,
                warehouse_name=warehouse.warehouse_name,
                product_id=event.product_id,
                product_code=event.product_code or product.product_code,
                product_name=product.product_name,
                barcode=product.barcode,
                event_type=event.event_type,
                source_type=event.source_type,
                source_id=event.source_id,
                source_line_id=event.source_line_id,
                stock_status=event.stock_status,
                qty=event.qty_delta,
                idempotency_key=event.idempotency_key,
                event_reason=event.event_reason,
                memo=event.memo,
                created_at=event.created_at,
                created_by=event.created_by,
            )
            for event, client, warehouse, product in rows
        ],
        total_count=total_count,
        page=safe_page,
        page_size=safe_page_size,
    )
    return response.model_dump()


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None
