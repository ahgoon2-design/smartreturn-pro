from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.inventory import CurrentInventory, InventoryEvent
from app.models.master import Client, Product, ProductBarcode, Warehouse


def find_event_by_idempotency_key(db: Session, idempotency_key: str) -> InventoryEvent | None:
    return db.query(InventoryEvent).filter(InventoryEvent.idempotency_key == idempotency_key).one_or_none()


def create_inventory_event(db: Session, event: InventoryEvent) -> InventoryEvent:
    db.add(event)
    db.flush()
    return event


def get_current_inventory(
    db: Session,
    *,
    client_id: int,
    warehouse_id: int,
    location_id: int | None,
    product_id: int,
    stock_status: str,
) -> CurrentInventory | None:
    query = db.query(CurrentInventory).filter(
        CurrentInventory.client_id == client_id,
        CurrentInventory.warehouse_id == warehouse_id,
        CurrentInventory.product_id == product_id,
        CurrentInventory.stock_status == stock_status,
    )
    if location_id is None:
        query = query.filter(CurrentInventory.location_id.is_(None))
    else:
        query = query.filter(CurrentInventory.location_id == location_id)
    return query.one_or_none()


def increase_current_inventory(
    db: Session,
    *,
    agency_id: int | None = None,
    client_id: int,
    warehouse_id: int,
    location_id: int | None,
    product_id: int,
    stock_status: str,
    qty_delta: int,
) -> CurrentInventory:
    current = get_current_inventory(
        db,
        client_id=client_id,
        warehouse_id=warehouse_id,
        location_id=location_id,
        product_id=product_id,
        stock_status=stock_status,
    )
    if current is None:
        current = CurrentInventory(
            agency_id=agency_id,
            client_id=client_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            product_id=product_id,
            stock_status=stock_status,
            qty_on_hand=qty_delta,
        )
        db.add(current)
    else:
        if current.agency_id is None and agency_id is not None:
            current.agency_id = agency_id
        current.qty_on_hand += qty_delta
    db.flush()
    return current


def list_current_inventory(
    db: Session,
    *,
    agency_id: int | None = None,
    client_id: int | None = None,
    warehouse_id: int | None = None,
    product_code: str | None = None,
    barcode: str | None = None,
    keyword: str | None = None,
    stock_status: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[tuple[CurrentInventory, Client, Warehouse, Product]], int]:
    query = (
        db.query(CurrentInventory, Client, Warehouse, Product)
        .join(Client, Client.id == CurrentInventory.client_id)
        .join(Warehouse, Warehouse.id == CurrentInventory.warehouse_id)
        .join(Product, Product.id == CurrentInventory.product_id)
    )

    if client_id is not None:
        query = query.filter(CurrentInventory.client_id == client_id)
    if agency_id is not None:
        query = query.filter(CurrentInventory.agency_id == agency_id)
    if warehouse_id is not None:
        query = query.filter(CurrentInventory.warehouse_id == warehouse_id)
    if product_code:
        query = query.filter(Product.product_code.ilike(f"%{product_code}%"))
    if barcode:
        barcode_like = f"%{barcode}%"
        query = query.filter(
            or_(
                Product.barcode.ilike(barcode_like),
                Product.id.in_(
                    db.query(ProductBarcode.product_id).filter(
                        ProductBarcode.barcode.ilike(barcode_like),
                    )
                ),
            )
        )
    if keyword:
        keyword_like = f"%{keyword}%"
        query = query.filter(
            or_(
                Client.client_name.ilike(keyword_like),
                Client.client_code.ilike(keyword_like),
                Warehouse.warehouse_name.ilike(keyword_like),
                Warehouse.warehouse_code.ilike(keyword_like),
                Product.product_code.ilike(keyword_like),
                Product.product_name.ilike(keyword_like),
                Product.barcode.ilike(keyword_like),
                Product.id.in_(
                    db.query(ProductBarcode.product_id).filter(
                        ProductBarcode.barcode.ilike(keyword_like),
                    )
                ),
            )
        )
    if stock_status:
        query = query.filter(CurrentInventory.stock_status == stock_status)

    total_count = query.with_entities(func.count()).scalar() or 0
    rows = (
        query.order_by(Client.client_name, Warehouse.warehouse_name, Product.product_code, CurrentInventory.stock_status)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total_count


def list_current_inventory_aggregated(
    db: Session,
    *,
    agency_id: int | None = None,
    client_id: int | None = None,
    product_code: str | None = None,
    barcode: str | None = None,
    keyword: str | None = None,
    stock_status: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list, int]:
    """창고 미지정 조회용 합산 결과.

    같은 client_id+product_id+stock_status를 창고를 가로질러 SUM(qty_on_hand)로 합산한다.
    순수 조회용 집계이며 current_inventory를 변경하지 않는다(재고 계산/반영 로직과 무관).
    창고 정보는 단일값이 없으므로 합산한 창고 수(warehouse_count)만 함께 돌려준다.
    """
    query = (
        db.query(
            CurrentInventory.client_id.label("client_id"),
            Client.client_code.label("client_code"),
            Client.client_name.label("client_name"),
            CurrentInventory.product_id.label("product_id"),
            Product.product_code.label("product_code"),
            Product.product_name.label("product_name"),
            Product.barcode.label("barcode"),
            CurrentInventory.stock_status.label("stock_status"),
            func.coalesce(func.sum(CurrentInventory.qty_on_hand), 0).label("qty"),
            func.count(func.distinct(CurrentInventory.warehouse_id)).label("warehouse_count"),
        )
        .join(Client, Client.id == CurrentInventory.client_id)
        .join(Product, Product.id == CurrentInventory.product_id)
    )

    if client_id is not None:
        query = query.filter(CurrentInventory.client_id == client_id)
    if agency_id is not None:
        query = query.filter(CurrentInventory.agency_id == agency_id)
    if product_code:
        query = query.filter(Product.product_code.ilike(f"%{product_code}%"))
    if barcode:
        barcode_like = f"%{barcode}%"
        query = query.filter(
            or_(
                Product.barcode.ilike(barcode_like),
                Product.id.in_(
                    db.query(ProductBarcode.product_id).filter(
                        ProductBarcode.barcode.ilike(barcode_like),
                    )
                ),
            )
        )
    if keyword:
        # 창고 미지정 합산 모드에는 창고 조인이 없으므로 keyword는 고객사/상품/바코드만 검색한다.
        keyword_like = f"%{keyword}%"
        query = query.filter(
            or_(
                Client.client_name.ilike(keyword_like),
                Client.client_code.ilike(keyword_like),
                Product.product_code.ilike(keyword_like),
                Product.product_name.ilike(keyword_like),
                Product.barcode.ilike(keyword_like),
                Product.id.in_(
                    db.query(ProductBarcode.product_id).filter(
                        ProductBarcode.barcode.ilike(keyword_like),
                    )
                ),
            )
        )
    if stock_status:
        query = query.filter(CurrentInventory.stock_status == stock_status)

    query = query.group_by(
        CurrentInventory.client_id,
        Client.client_code,
        Client.client_name,
        CurrentInventory.product_id,
        Product.product_code,
        Product.product_name,
        Product.barcode,
        CurrentInventory.stock_status,
    )

    total_count = db.query(func.count()).select_from(query.subquery()).scalar() or 0
    rows = (
        query.order_by(Client.client_name, Product.product_code, CurrentInventory.stock_status)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total_count


def list_inventory_events(
    db: Session,
    *,
    agency_id: int | None = None,
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
) -> tuple[list[tuple[InventoryEvent, Client, Warehouse, Product]], int]:
    query = (
        db.query(InventoryEvent, Client, Warehouse, Product)
        .join(Client, Client.id == InventoryEvent.client_id)
        .join(Warehouse, Warehouse.id == InventoryEvent.warehouse_id)
        .join(Product, Product.id == InventoryEvent.product_id)
    )

    if client_id is not None:
        query = query.filter(InventoryEvent.client_id == client_id)
    if agency_id is not None:
        query = query.filter(InventoryEvent.agency_id == agency_id)
    if warehouse_id is not None:
        query = query.filter(InventoryEvent.warehouse_id == warehouse_id)
    if product_code:
        query = query.filter(Product.product_code.ilike(f"%{product_code}%"))
    if barcode:
        barcode_like = f"%{barcode}%"
        query = query.filter(
            or_(
                Product.barcode.ilike(barcode_like),
                Product.id.in_(
                    db.query(ProductBarcode.product_id).filter(
                        ProductBarcode.barcode.ilike(barcode_like),
                    )
                ),
            )
        )
    if keyword:
        keyword_like = f"%{keyword}%"
        query = query.filter(
            or_(
                InventoryEvent.event_no.ilike(keyword_like),
                InventoryEvent.event_type.ilike(keyword_like),
                InventoryEvent.source_type.ilike(keyword_like),
                InventoryEvent.idempotency_key.ilike(keyword_like),
                Client.client_name.ilike(keyword_like),
                Client.client_code.ilike(keyword_like),
                Warehouse.warehouse_name.ilike(keyword_like),
                Warehouse.warehouse_code.ilike(keyword_like),
                Product.product_code.ilike(keyword_like),
                Product.product_name.ilike(keyword_like),
                Product.barcode.ilike(keyword_like),
                Product.id.in_(
                    db.query(ProductBarcode.product_id).filter(
                        ProductBarcode.barcode.ilike(keyword_like),
                    )
                ),
            )
        )
    if event_type:
        query = query.filter(InventoryEvent.event_type == event_type)
    if source_type:
        query = query.filter(InventoryEvent.source_type == source_type)
    if date_from is not None:
        query = query.filter(InventoryEvent.created_at >= date_from)
    if date_to is not None:
        query = query.filter(InventoryEvent.created_at <= date_to)

    total_count = query.with_entities(func.count()).scalar() or 0
    rows = (
        query.order_by(InventoryEvent.created_at.desc(), InventoryEvent.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total_count
