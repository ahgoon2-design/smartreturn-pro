"""P0 기준정보 read-only service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.auth_context import resolve_effective_client_id
from app.core.exceptions import AuthError, ClientScopeDeniedError
from app.core.permissions import require_permission, require_roles
from app.repositories import master_repository as repo
from app.schemas.auth import AuthContext
from app.schemas.master import (
    ClientDetail,
    ClientSummary,
    ClientWarehouseSummary,
    CommonCodeGroupSummary,
    CommonCodeSummary,
    PageData,
    ProductBarcodeCreateRequest,
    ProductBarcodeDto,
    ProductBarcodeUpdateRequest,
    ProductCreateRequest,
    ProductDetail,
    ProductSummary,
    ProductUpdateRequest,
    WarehouseSummary,
)


def _dump(model) -> dict:
    return model.model_dump()


def _normalize_barcode(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _require_product_manage(auth: AuthContext) -> None:
    require_roles(auth, {"SUPER_ADMIN", "INTERNAL_ADMIN", "INTERNAL_WORKER"})
    require_permission(auth, "MASTER_MANAGE")
    require_permission(auth, "PRODUCT_MANAGE")


def _business_error(result_code: str, message: str, status_code: int = 400) -> AuthError:
    return AuthError(message, result_code=result_code, status_code=status_code)


def _ensure_active_client(db: Session, client_id: int):
    client = repo.get_client(db, client_id)
    if client is None:
        raise _business_error("MASTER_CLIENT_NOT_FOUND", "고객사를 찾을 수 없습니다.", 404)
    if not client.active_yn:
        raise _business_error("MASTER_CLIENT_INACTIVE", "사용중지된 고객사에는 상품을 등록할 수 없습니다.")
    return client


def _ensure_product_code_available(
    db: Session,
    *,
    client_id: int,
    product_code: str,
    exclude_product_id: int | None = None,
) -> None:
    if repo.find_product_by_code(db, client_id, product_code, exclude_product_id=exclude_product_id):
        raise _business_error("MASTER_PRODUCT_CODE_DUPLICATED", "이미 등록된 상품코드입니다.")


def _ensure_barcode_available(
    db: Session,
    *,
    client_id: int,
    barcode: str | None,
    exclude_product_id: int | None = None,
    exclude_barcode_id: int | None = None,
) -> str | None:
    barcode_norm = _normalize_barcode(barcode)
    if barcode_norm is None:
        return None
    if repo.find_product_by_barcode(db, client_id, barcode_norm, exclude_product_id=exclude_product_id):
        raise _business_error("MASTER_PRODUCT_BARCODE_DUPLICATED", "이미 등록된 대표 바코드입니다.")
    if repo.find_product_barcode_by_norm(db, client_id, barcode_norm, exclude_barcode_id=exclude_barcode_id):
        raise _business_error("MASTER_PRODUCT_BARCODE_DUPLICATED", "이미 등록된 추가 바코드입니다.")
    return barcode_norm


def _product_detail_for_manage(db: Session, auth: AuthContext, product_id: int) -> dict:
    detail = get_product_detail(db, auth, product_id)
    if detail is None:
        raise _business_error("MASTER_PRODUCT_NOT_FOUND", "상품을 찾을 수 없습니다.", 404)
    return detail


def _barcode_dto(product_barcode) -> dict:
    return _dump(
        ProductBarcodeDto(
            barcode_id=product_barcode.id,
            barcode=product_barcode.barcode,
            barcode_type=product_barcode.barcode_type,
            unit_qty=product_barcode.unit_qty,
            active_yn=product_barcode.active_yn,
            remarks=product_barcode.remarks,
        )
    )


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


def create_product(db: Session, auth: AuthContext, request: ProductCreateRequest) -> dict:
    _require_product_manage(auth)
    resolve_effective_client_id(auth, request.client_id)
    _ensure_active_client(db, request.client_id)
    _ensure_product_code_available(db, client_id=request.client_id, product_code=request.product_code)
    barcode = _ensure_barcode_available(db, client_id=request.client_id, barcode=request.barcode)

    try:
        product = repo.create_product(
            db,
            client_id=request.client_id,
            product_code=request.product_code,
            product_name=request.product_name,
            barcode=barcode,
            specification=request.specification,
            unit_name=request.unit_name,
            remarks=request.remarks,
        )
        db.commit()
        return _product_detail_for_manage(db, auth, product.id)
    except Exception:
        db.rollback()
        raise


def update_product(db: Session, auth: AuthContext, product_id: int, request: ProductUpdateRequest) -> dict:
    _require_product_manage(auth)
    product = repo.get_product_by_id(db, product_id)
    if product is None:
        raise _business_error("MASTER_PRODUCT_NOT_FOUND", "상품을 찾을 수 없습니다.", 404)
    resolve_effective_client_id(auth, product.client_id)

    values = request.model_dump(exclude_unset=True)
    if "product_code" in values and values["product_code"] != product.product_code:
        _ensure_product_code_available(
            db,
            client_id=product.client_id,
            product_code=str(values["product_code"]),
            exclude_product_id=product.id,
        )
    if "barcode" in values:
        values["barcode"] = _ensure_barcode_available(
            db,
            client_id=product.client_id,
            barcode=values["barcode"],  # type: ignore[arg-type]
            exclude_product_id=product.id,
        )

    try:
        repo.update_product(db, product, values)
        db.commit()
        return _product_detail_for_manage(db, auth, product.id)
    except Exception:
        db.rollback()
        raise


def set_product_active(db: Session, auth: AuthContext, product_id: int, active_yn: bool) -> dict:
    _require_product_manage(auth)
    product = repo.get_product_by_id(db, product_id)
    if product is None:
        raise _business_error("MASTER_PRODUCT_NOT_FOUND", "상품을 찾을 수 없습니다.", 404)
    resolve_effective_client_id(auth, product.client_id)

    try:
        repo.set_product_active(db, product, active_yn)
        db.commit()
        return _product_detail_for_manage(db, auth, product.id)
    except Exception:
        db.rollback()
        raise


def create_product_barcode(db: Session, auth: AuthContext, request: ProductBarcodeCreateRequest) -> dict:
    _require_product_manage(auth)
    product = repo.get_product_by_id(db, request.product_id)
    if product is None:
        raise _business_error("MASTER_PRODUCT_NOT_FOUND", "상품을 찾을 수 없습니다.", 404)
    resolve_effective_client_id(auth, product.client_id)
    barcode_norm = _ensure_barcode_available(db, client_id=product.client_id, barcode=request.barcode)
    if barcode_norm is None:
        raise _business_error("MASTER_PRODUCT_BARCODE_INVALID", "바코드 값이 필요합니다.")

    try:
        product_barcode = repo.create_product_barcode(
            db,
            client_id=product.client_id,
            product_id=product.id,
            barcode=request.barcode,
            barcode_norm=barcode_norm,
            barcode_type=request.barcode_type,
            unit_qty=request.unit_qty,
            remarks=request.remarks,
        )
        db.commit()
        return _barcode_dto(product_barcode)
    except Exception:
        db.rollback()
        raise


def update_product_barcode(
    db: Session,
    auth: AuthContext,
    barcode_id: int,
    request: ProductBarcodeUpdateRequest,
) -> dict:
    _require_product_manage(auth)
    product_barcode = repo.get_product_barcode_by_id(db, barcode_id)
    if product_barcode is None:
        raise _business_error("MASTER_PRODUCT_BARCODE_NOT_FOUND", "상품바코드를 찾을 수 없습니다.", 404)
    product = repo.get_product_by_id(db, product_barcode.product_id)
    if product is None:
        raise _business_error("MASTER_PRODUCT_NOT_FOUND", "상품을 찾을 수 없습니다.", 404)
    resolve_effective_client_id(auth, product.client_id)

    values = request.model_dump(exclude_unset=True)
    if "barcode" in values:
        barcode_norm = _ensure_barcode_available(
            db,
            client_id=product.client_id,
            barcode=values["barcode"],  # type: ignore[arg-type]
            exclude_barcode_id=product_barcode.id,
        )
        if barcode_norm is None:
            raise _business_error("MASTER_PRODUCT_BARCODE_INVALID", "바코드 값이 필요합니다.")
        values["barcode_norm"] = barcode_norm

    try:
        repo.update_product_barcode(db, product_barcode, values)
        db.commit()
        return _barcode_dto(product_barcode)
    except Exception:
        db.rollback()
        raise


def set_product_barcode_active(db: Session, auth: AuthContext, barcode_id: int, active_yn: bool) -> dict:
    _require_product_manage(auth)
    product_barcode = repo.get_product_barcode_by_id(db, barcode_id)
    if product_barcode is None:
        raise _business_error("MASTER_PRODUCT_BARCODE_NOT_FOUND", "상품바코드를 찾을 수 없습니다.", 404)
    product = repo.get_product_by_id(db, product_barcode.product_id)
    if product is None:
        raise _business_error("MASTER_PRODUCT_NOT_FOUND", "상품을 찾을 수 없습니다.", 404)
    resolve_effective_client_id(auth, product.client_id)

    try:
        repo.set_product_barcode_active(db, product_barcode, active_yn)
        db.commit()
        return _barcode_dto(product_barcode)
    except Exception:
        db.rollback()
        raise


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
