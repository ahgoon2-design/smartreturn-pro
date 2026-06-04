from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.inventory import CurrentInventory, InventoryEvent


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
            client_id=client_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            product_id=product_id,
            stock_status=stock_status,
            qty_on_hand=qty_delta,
        )
        db.add(current)
    else:
        current.qty_on_hand += qty_delta
    db.flush()
    return current
