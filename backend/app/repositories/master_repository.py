"""P0 기준정보 read-only repository."""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.master import (
    Client,
    ClientWarehouseSetting,
    CommonCode,
    CommonCodeGroup,
    Product,
    ProductBarcode,
    Warehouse,
)


def _active(query, model, active_only: bool):
    if active_only:
        return query.filter(model.active_yn.is_(True))
    return query


def list_clients(db: Session, active_only: bool = True) -> list[Client]:
    query = db.query(Client)
    query = _active(query, Client, active_only)
    return query.order_by(Client.client_name, Client.id).all()


def get_client(db: Session, client_id: int) -> Client | None:
    return db.query(Client).filter(Client.id == client_id).one_or_none()


def get_client_by_id(db: Session, client_id: int) -> Client | None:
    return get_client(db, client_id)


def find_client_by_code(db: Session, client_code: str) -> Client | None:
    return db.query(Client).filter(Client.client_code == client_code).one_or_none()


def create_client(
    db: Session,
    *,
    client_code: str,
    client_name: str,
    business_no: str | None = None,
    contact_name: str | None = None,
    contact_phone: str | None = None,
    contact_email: str | None = None,
    use_oms: bool = False,
    use_wms: bool = True,
    use_returns: bool = True,
    use_settlement: bool = False,
    remarks: str | None = None,
) -> Client:
    client = Client(
        client_code=client_code,
        client_name=client_name,
        business_no=business_no,
        contact_name=contact_name,
        contact_phone=contact_phone,
        contact_email=contact_email,
        use_oms=use_oms,
        use_wms=use_wms,
        use_returns=use_returns,
        use_settlement=use_settlement,
        remarks=remarks,
        active_yn=True,
    )
    db.add(client)
    db.flush()
    return client


def update_client(db: Session, client: Client, values: dict[str, object]) -> Client:
    for field, value in values.items():
        setattr(client, field, value)
    db.flush()
    return client


def set_client_active(db: Session, client: Client, active_yn: bool) -> Client:
    client.active_yn = active_yn
    db.flush()
    return client


def list_warehouses(db: Session, active_only: bool = True) -> list[Warehouse]:
    query = db.query(Warehouse)
    query = _active(query, Warehouse, active_only)
    return query.order_by(Warehouse.warehouse_name, Warehouse.id).all()


def get_warehouse_by_id(db: Session, warehouse_id: int) -> Warehouse | None:
    return db.query(Warehouse).filter(Warehouse.id == warehouse_id).one_or_none()


def find_warehouse_by_code(db: Session, warehouse_code: str) -> Warehouse | None:
    return db.query(Warehouse).filter(Warehouse.warehouse_code == warehouse_code).one_or_none()


def create_warehouse(
    db: Session,
    *,
    warehouse_code: str,
    warehouse_name: str,
    warehouse_type: str | None = None,
    address: str | None = None,
    remarks: str | None = None,
) -> Warehouse:
    warehouse = Warehouse(
        warehouse_code=warehouse_code,
        warehouse_name=warehouse_name,
        warehouse_type=warehouse_type,
        address=address,
        remarks=remarks,
        active_yn=True,
    )
    db.add(warehouse)
    db.flush()
    return warehouse


def update_warehouse(db: Session, warehouse: Warehouse, values: dict[str, object]) -> Warehouse:
    for field, value in values.items():
        setattr(warehouse, field, value)
    db.flush()
    return warehouse


def set_warehouse_active(db: Session, warehouse: Warehouse, active_yn: bool) -> Warehouse:
    warehouse.active_yn = active_yn
    db.flush()
    return warehouse


def list_client_warehouses(
    db: Session,
    client_id: int,
    active_only: bool = True,
) -> list[tuple[ClientWarehouseSetting, Client, Warehouse]]:
    query = (
        db.query(ClientWarehouseSetting, Client, Warehouse)
        .join(Client, Client.id == ClientWarehouseSetting.client_id)
        .join(Warehouse, Warehouse.id == ClientWarehouseSetting.warehouse_id)
        .filter(ClientWarehouseSetting.client_id == client_id)
    )
    if active_only:
        query = query.filter(
            ClientWarehouseSetting.active_yn.is_(True),
            Client.active_yn.is_(True),
            Warehouse.active_yn.is_(True),
        )
    return query.order_by(ClientWarehouseSetting.is_default.desc(), Warehouse.warehouse_name).all()


def list_products(
    db: Session,
    client_id: int | None = None,
    keyword: str | None = None,
    active_only: bool = True,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[tuple[Product, Client]], int]:
    query = db.query(Product, Client).join(Client, Client.id == Product.client_id)
    if client_id is not None:
        query = query.filter(Product.client_id == client_id)
    if active_only:
        query = query.filter(Product.active_yn.is_(True), Client.active_yn.is_(True))
    if keyword:
        like_keyword = f"%{keyword}%"
        query = query.filter(
            or_(
                Product.product_code.ilike(like_keyword),
                Product.product_name.ilike(like_keyword),
                Product.barcode.ilike(like_keyword),
            )
        )
    total_count = query.count()
    items = (
        query.order_by(Client.client_name, Product.product_name, Product.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total_count


def get_product(db: Session, product_id: int) -> tuple[Product, Client] | None:
    return (
        db.query(Product, Client)
        .join(Client, Client.id == Product.client_id)
        .filter(Product.id == product_id)
        .one_or_none()
    )


def get_product_by_id(db: Session, product_id: int) -> Product | None:
    return db.query(Product).filter(Product.id == product_id).one_or_none()


def find_product_by_code(
    db: Session,
    client_id: int,
    product_code: str,
    exclude_product_id: int | None = None,
) -> Product | None:
    query = db.query(Product).filter(Product.client_id == client_id, Product.product_code == product_code)
    if exclude_product_id is not None:
        query = query.filter(Product.id != exclude_product_id)
    return query.one_or_none()


def find_product_by_barcode(
    db: Session,
    client_id: int,
    barcode: str,
    exclude_product_id: int | None = None,
) -> Product | None:
    query = db.query(Product).filter(Product.client_id == client_id, Product.barcode == barcode)
    if exclude_product_id is not None:
        query = query.filter(Product.id != exclude_product_id)
    return query.one_or_none()


def create_product(
    db: Session,
    *,
    client_id: int,
    product_code: str,
    product_name: str,
    barcode: str | None = None,
    specification: str | None = None,
    unit_name: str | None = None,
    remarks: str | None = None,
) -> Product:
    product = Product(
        client_id=client_id,
        product_code=product_code,
        product_name=product_name,
        barcode=barcode,
        specification=specification,
        unit_name=unit_name,
        remarks=remarks,
        active_yn=True,
    )
    db.add(product)
    db.flush()
    return product


def update_product(db: Session, product: Product, values: dict[str, object]) -> Product:
    for field, value in values.items():
        setattr(product, field, value)
    db.flush()
    return product


def set_product_active(db: Session, product: Product, active_yn: bool) -> Product:
    product.active_yn = active_yn
    db.flush()
    return product


def list_product_barcodes(db: Session, product_id: int, active_only: bool = True) -> list[ProductBarcode]:
    query = db.query(ProductBarcode).filter(ProductBarcode.product_id == product_id)
    query = _active(query, ProductBarcode, active_only)
    return query.order_by(ProductBarcode.barcode_type, ProductBarcode.id).all()


def get_product_barcode_by_id(db: Session, barcode_id: int) -> ProductBarcode | None:
    return db.query(ProductBarcode).filter(ProductBarcode.id == barcode_id).one_or_none()


def find_product_barcode_by_norm(
    db: Session,
    client_id: int,
    barcode_norm: str,
    exclude_barcode_id: int | None = None,
) -> ProductBarcode | None:
    query = db.query(ProductBarcode).filter(
        ProductBarcode.client_id == client_id,
        ProductBarcode.barcode_norm == barcode_norm,
    )
    if exclude_barcode_id is not None:
        query = query.filter(ProductBarcode.id != exclude_barcode_id)
    return query.one_or_none()


def create_product_barcode(
    db: Session,
    *,
    client_id: int,
    product_id: int,
    barcode: str,
    barcode_norm: str,
    barcode_type: str,
    unit_qty: int,
    remarks: str | None = None,
) -> ProductBarcode:
    product_barcode = ProductBarcode(
        client_id=client_id,
        product_id=product_id,
        barcode=barcode,
        barcode_norm=barcode_norm,
        barcode_type=barcode_type,
        unit_qty=unit_qty,
        remarks=remarks,
        active_yn=True,
    )
    db.add(product_barcode)
    db.flush()
    return product_barcode


def update_product_barcode(
    db: Session,
    product_barcode: ProductBarcode,
    values: dict[str, object],
) -> ProductBarcode:
    for field, value in values.items():
        setattr(product_barcode, field, value)
    db.flush()
    return product_barcode


def set_product_barcode_active(
    db: Session,
    product_barcode: ProductBarcode,
    active_yn: bool,
) -> ProductBarcode:
    product_barcode.active_yn = active_yn
    db.flush()
    return product_barcode


def list_common_code_groups(db: Session, active_only: bool = True) -> list[CommonCodeGroup]:
    query = db.query(CommonCodeGroup)
    query = _active(query, CommonCodeGroup, active_only)
    return query.order_by(CommonCodeGroup.group_code).all()


def get_common_code_group_by_id(db: Session, group_id: int) -> CommonCodeGroup | None:
    return db.query(CommonCodeGroup).filter(CommonCodeGroup.id == group_id).one_or_none()


def find_common_code_group_by_code(db: Session, group_code: str) -> CommonCodeGroup | None:
    return db.query(CommonCodeGroup).filter(CommonCodeGroup.group_code == group_code).one_or_none()


def create_common_code_group(
    db: Session,
    *,
    group_code: str,
    group_name: str,
    description: str | None = None,
) -> CommonCodeGroup:
    group = CommonCodeGroup(
        group_code=group_code,
        group_name=group_name,
        description=description,
        active_yn=True,
    )
    db.add(group)
    db.flush()
    return group


def update_common_code_group(
    db: Session,
    group: CommonCodeGroup,
    values: dict[str, object],
) -> CommonCodeGroup:
    for field, value in values.items():
        setattr(group, field, value)
    db.flush()
    return group


def set_common_code_group_active(
    db: Session,
    group: CommonCodeGroup,
    active_yn: bool,
) -> CommonCodeGroup:
    group.active_yn = active_yn
    db.flush()
    return group


def list_common_codes(
    db: Session,
    group_code: str | None = None,
    active_only: bool = True,
) -> list[tuple[CommonCode, CommonCodeGroup]]:
    query = db.query(CommonCode, CommonCodeGroup).join(CommonCodeGroup, CommonCodeGroup.id == CommonCode.group_id)
    if group_code:
        query = query.filter(CommonCodeGroup.group_code == group_code)
    if active_only:
        query = query.filter(CommonCode.active_yn.is_(True), CommonCodeGroup.active_yn.is_(True))
    return query.order_by(CommonCodeGroup.group_code, CommonCode.sort_order, CommonCode.id).all()


def get_common_code_by_id(db: Session, code_id: int) -> CommonCode | None:
    return db.query(CommonCode).filter(CommonCode.id == code_id).one_or_none()


def find_common_code_by_value(
    db: Session,
    group_id: int,
    code_value: str,
    exclude_code_id: int | None = None,
) -> CommonCode | None:
    query = db.query(CommonCode).filter(CommonCode.group_id == group_id, CommonCode.code_value == code_value)
    if exclude_code_id is not None:
        query = query.filter(CommonCode.id != exclude_code_id)
    return query.one_or_none()


def create_common_code(
    db: Session,
    *,
    group_id: int,
    code_value: str,
    code_name: str,
    sort_order: int = 0,
    description: str | None = None,
) -> CommonCode:
    code = CommonCode(
        group_id=group_id,
        code_value=code_value,
        code_name=code_name,
        sort_order=sort_order,
        system_yn=False,
        locked_yn=False,
        active_yn=True,
        description=description,
    )
    db.add(code)
    db.flush()
    return code


def update_common_code(db: Session, code: CommonCode, values: dict[str, object]) -> CommonCode:
    for field, value in values.items():
        setattr(code, field, value)
    db.flush()
    return code


def set_common_code_active(db: Session, code: CommonCode, active_yn: bool) -> CommonCode:
    code.active_yn = active_yn
    db.flush()
    return code
