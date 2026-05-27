"""P0 기준정보 read-only service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.auth_context import resolve_effective_client_id
from app.core.exceptions import ClientScopeDeniedError
from app.repositories import master_repository as repo
from app.schemas.auth import AuthContext
from app.schemas.master import (
    ClientDetail,
    ClientSummary,
    ClientWarehouseSummary,
    CommonCodeGroupSummary,
    CommonCodeSummary,
    PageData,
    ProductBarcodeDto,
    ProductDetail,
    ProductSummary,
    WarehouseSummary,
)


def _dump(model) -> dict:
    return model.model_dump()


def _client_summary(client) -> ClientSummary:
    return ClientSummary(
        client_id=client.id,
        client_code=client.client_code,
        client_name=client.client_name,
        active_yn=client.active_yn,
    )


def _client_detail(client) -> ClientDetail:
    return ClientDetail(
        client_id=client.id,
        client_code=client.client_code,
        client_name=client.client_name,
        business_no=client.business_no,
        contact_name=client.contact_name,
        contact_phone=client.contact_phone,
        contact_email=client.contact_email,
        use_oms=client.use_oms,
        use_wms=client.use_wms,
        use_returns=client.use_returns,
        use_settlement=client.use_settlement,
        active_yn=client.active_yn,
        remarks=client.remarks,
    )


def get_accessible_clients(db: Session, auth: AuthContext) -> list[dict]:
    if auth.is_internal_user:
        return [_dump(_client_summary(client)) for client in repo.list_clients(db)]
    if auth.is_client_user and auth.client_id is not None:
        client = repo.get_client(db, auth.client_id)
        return [_dump(_client_summary(client))] if client and client.active_yn else []
    raise ClientScopeDeniedError("고객사 조회 범위를 확인할 수 없습니다.")


def get_client_detail(db: Session, auth: AuthContext, client_id: int) -> dict | None:
    resolve_effective_client_id(auth, client_id)
    client = repo.get_client(db, client_id)
    if client is None:
        return None
    return _dump(_client_detail(client))


def get_accessible_warehouses(db: Session, auth: AuthContext) -> list[dict]:
    if not auth.is_internal_user:
        raise ClientScopeDeniedError("전체 창고 목록은 내부 운영자만 조회할 수 있습니다.")
    return [
        _dump(
            WarehouseSummary(
                warehouse_id=warehouse.id,
                warehouse_code=warehouse.warehouse_code,
                warehouse_name=warehouse.warehouse_name,
                warehouse_type=warehouse.warehouse_type,
                active_yn=warehouse.active_yn,
            )
        )
        for warehouse in repo.list_warehouses(db)
    ]


def get_client_warehouses(db: Session, auth: AuthContext, client_id: int | None = None) -> list[dict]:
    effective_client_id = resolve_effective_client_id(auth, client_id)
    if effective_client_id is None:
        raise ClientScopeDeniedError("고객사 창고 조회에는 client_id가 필요합니다.")

    rows = repo.list_client_warehouses(db, effective_client_id)
    return [
        _dump(
            ClientWarehouseSummary(
                client_id=client.id,
                client_name=client.client_name,
                warehouse_id=warehouse.id,
                warehouse_code=warehouse.warehouse_code,
                warehouse_name=warehouse.warehouse_name,
                usage_type=setting.usage_type,
                is_default=setting.is_default,
                active_yn=setting.active_yn,
            )
        )
        for setting, client, warehouse in rows
    ]


def get_products(
    db: Session,
    auth: AuthContext,
    client_id: int | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    effective_client_id = resolve_effective_client_id(auth, client_id, allow_all_clients=True)
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 200)
    rows, total_count = repo.list_products(
        db,
        client_id=effective_client_id,
        keyword=keyword,
        page=safe_page,
        page_size=safe_page_size,
    )
    items = [
        _dump(
            ProductSummary(
                product_id=product.id,
                client_id=client.id,
                client_name=client.client_name,
                product_code=product.product_code,
                product_name=product.product_name,
                barcode=product.barcode,
                active_yn=product.active_yn,
            )
        )
        for product, client in rows
    ]
    return _dump(PageData(items=items, page=safe_page, page_size=safe_page_size, total_count=total_count))


def get_product_detail(db: Session, auth: AuthContext, product_id: int) -> dict | None:
    row = repo.get_product(db, product_id)
    if row is None:
        return None
    product, client = row
    resolve_effective_client_id(auth, product.client_id)
    barcodes = [
        ProductBarcodeDto(
            barcode_id=barcode.id,
            barcode=barcode.barcode,
            barcode_type=barcode.barcode_type,
            unit_qty=barcode.unit_qty,
            active_yn=barcode.active_yn,
            remarks=barcode.remarks,
        )
        for barcode in repo.list_product_barcodes(db, product.id)
    ]
    return _dump(
        ProductDetail(
            product_id=product.id,
            client_id=client.id,
            client_name=client.client_name,
            product_code=product.product_code,
            product_name=product.product_name,
            barcode=product.barcode,
            active_yn=product.active_yn,
            specification=product.specification,
            unit_name=product.unit_name,
            remarks=product.remarks,
            barcodes=barcodes,
        )
    )


def get_common_code_groups(db: Session, auth: AuthContext) -> list[dict]:
    return [
        _dump(
            CommonCodeGroupSummary(
                group_id=group.id,
                group_code=group.group_code,
                group_name=group.group_name,
                active_yn=group.active_yn,
            )
        )
        for group in repo.list_common_code_groups(db)
    ]


def get_common_codes(db: Session, auth: AuthContext, group_code: str | None = None) -> list[dict]:
    return [
        _dump(
            CommonCodeSummary(
                code_id=code.id,
                group_code=group.group_code,
                code_value=code.code_value,
                code_name=code.code_name,
                sort_order=code.sort_order,
                active_yn=code.active_yn,
            )
        )
        for code, group in repo.list_common_codes(db, group_code=group_code)
    ]
