"""P0 기준정보 read-only service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.auth_context import resolve_effective_agency_id, resolve_effective_client_id
from app.core.exceptions import AuthError, ClientScopeDeniedError
from app.core.permissions import require_permission, require_roles
from app.repositories import master_repository as repo
from app.schemas.auth import AuthContext
from app.schemas.master import (
    ClientCreateRequest,
    ClientDetail,
    ClientUnitCreateRequest,
    ClientUnitResponse,
    ClientUnitUpdateRequest,
    ClientWarehouseSettingNestedCreateRequest,
    ClientWarehouseSettingCreateRequest,
    ClientWarehouseSettingResponse,
    ClientWarehouseSettingUpdateRequest,
    ClientSummary,
    ClientUpdateRequest,
    ClientWarehouseSummary,
    CommonCodeCreateRequest,
    CommonCodeGroupCreateRequest,
    CommonCodeGroupUpdateRequest,
    CommonCodeGroupSummary,
    CommonCodeUpdateRequest,
    CommonCodeSummary,
    PageData,
    ProductBarcodeCreateRequest,
    ProductBarcodeDto,
    ProductBarcodeUpdateRequest,
    ProductCreateRequest,
    ProductDetail,
    ProductSummary,
    ProductUpdateRequest,
    ReturnJudgmentWarehouseRouteCreateRequest,
    ReturnJudgmentWarehouseRouteResponse,
    ReturnJudgmentWarehouseRouteUpdateRequest,
    WarehouseCreateRequest,
    WarehouseOptionResponse,
    WarehouseSummary,
    WarehouseUpdateRequest,
)


CLIENT_WAREHOUSE_USAGE_TYPES = {
    "INBOUND",
    "OUTBOUND",
    "RETURN_GOOD",
    "RETURN_HOLD",
    "RETURN_DISPOSAL",
    "RETURN_REFURB",
    "RETURN_MANUFACTURER",
    "SAMPLE",
    "STORAGE",
}

CLIENT_WAREHOUSE_USAGE_TYPE_LABELS = {
    "INBOUND": "입고",
    "OUTBOUND": "출고",
    "RETURN_GOOD": "반품양품",
    "RETURN_HOLD": "보류",
    "RETURN_DISPOSAL": "폐기",
    "RETURN_REFURB": "리퍼",
    "RETURN_MANUFACTURER": "제조사반품",
    "SAMPLE": "샘플",
    "STORAGE": "보관",
}

RETURN_WAREHOUSE_ROUTE_JUDGMENT_CODES = {
    "GOOD",
    "REFURB",
    "REFURB_A",
    "REFURB_B",
    "REFURB_C",
    "SAMPLE",
    "MANUFACTURER_RETURN",
    "DISPOSAL",
    "HOLD",
    "DEFECTIVE",
}


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


def _require_client_manage(auth: AuthContext) -> None:
    require_roles(auth, {"SUPER_ADMIN", "INTERNAL_ADMIN"})
    require_permission(auth, "MASTER_MANAGE")
    require_permission(auth, "CLIENT_MANAGE")


def _require_warehouse_manage(auth: AuthContext) -> None:
    require_roles(auth, {"SUPER_ADMIN", "INTERNAL_ADMIN"})
    require_permission(auth, "MASTER_MANAGE")
    require_permission(auth, "WAREHOUSE_MANAGE")


def _require_common_code_manage(auth: AuthContext) -> None:
    require_roles(auth, {"SUPER_ADMIN", "INTERNAL_ADMIN"})
    require_permission(auth, "MASTER_MANAGE")
    require_permission(auth, "COMMON_CODE_MANAGE")


def _business_error(result_code: str, message: str, status_code: int = 400) -> AuthError:
    return AuthError(message, result_code=result_code, status_code=status_code)


def _ensure_active_client(db: Session, client_id: int):
    client = repo.get_client(db, client_id)
    if client is None:
        raise _business_error("MASTER_CLIENT_NOT_FOUND", "고객사를 찾을 수 없습니다.", 404)
    if not client.active_yn:
        raise _business_error("MASTER_CLIENT_INACTIVE", "사용중지된 고객사에는 상품을 등록할 수 없습니다.")
    return client


def _ensure_client_code_available(db: Session, client_code: str) -> None:
    if repo.find_client_by_code(db, client_code):
        raise _business_error("MASTER_CLIENT_CODE_DUPLICATED", "이미 등록된 고객사 코드입니다.")


def _ensure_warehouse_code_available(db: Session, warehouse_code: str) -> None:
    if repo.find_warehouse_by_code(db, warehouse_code):
        raise _business_error("MASTER_WAREHOUSE_CODE_DUPLICATED", "이미 등록된 창고 코드입니다.")


def _ensure_active_warehouse(db: Session, warehouse_id: int):
    warehouse = repo.get_warehouse_by_id(db, warehouse_id)
    if warehouse is None:
        raise _business_error("MASTER_WAREHOUSE_NOT_FOUND", "Warehouse not found.", 404)
    if not warehouse.active_yn:
        raise _business_error("MASTER_WAREHOUSE_INACTIVE", "Inactive warehouse cannot be linked.")
    return warehouse


def _ensure_client_warehouse_usage_type(usage_type: str) -> str:
    usage_type = usage_type.strip()
    if usage_type not in CLIENT_WAREHOUSE_USAGE_TYPES:
        raise _business_error("MASTER_CLIENT_WAREHOUSE_USAGE_TYPE_INVALID", "Invalid client warehouse usage_type.")
    return usage_type


def _ensure_client_warehouse_setting_available(
    db: Session,
    *,
    client_id: int,
    warehouse_id: int,
    usage_type: str,
    exclude_setting_id: int | None = None,
) -> None:
    if repo.find_client_warehouse_setting(
        db,
        client_id=client_id,
        warehouse_id=warehouse_id,
        usage_type=usage_type,
        exclude_setting_id=exclude_setting_id,
    ):
        raise _business_error("MASTER_CLIENT_WAREHOUSE_DUPLICATED", "Duplicated client warehouse setting.")


def _can_manage_client_warehouse(auth: AuthContext) -> bool:
    roles = set(auth.roles)
    permissions = set(auth.permissions)
    if "SUPER_ADMIN" in roles:
        return True
    return bool(
        roles & {"INTERNAL_ADMIN"}
        and {"MASTER_MANAGE", "WAREHOUSE_MANAGE"}.issubset(permissions)
    )


def _client_warehouse_allowed_actions(auth: AuthContext, setting, warehouse) -> dict[str, bool]:
    can_manage = _can_manage_client_warehouse(auth)
    can_set_default = can_manage and setting.active_yn and warehouse.active_yn and not setting.is_default
    return {
        "can_update": can_manage,
        "can_disable": can_manage and setting.active_yn and not setting.is_default,
        "can_enable": can_manage and not setting.active_yn,
        "can_set_default": can_set_default,
    }


def _usage_type_label(usage_type: str) -> str:
    return CLIENT_WAREHOUSE_USAGE_TYPE_LABELS.get(usage_type, usage_type)


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
            agency_id=product_barcode.agency_id,
            barcode=product_barcode.barcode,
            barcode_type=product_barcode.barcode_type,
            unit_qty=product_barcode.unit_qty,
            active_yn=product_barcode.active_yn,
            remarks=product_barcode.remarks,
        )
    )


def _client_summary(client) -> ClientSummary:
    agency = getattr(client, "_agency", None)
    return ClientSummary(
        client_id=client.id,
        agency_id=client.agency_id,
        agency_name=getattr(agency, "agency_name", None),
        client_code=client.client_code,
        client_name=client.client_name,
        active_yn=client.active_yn,
    )


def _client_detail(client) -> ClientDetail:
    agency = getattr(client, "_agency", None)
    return ClientDetail(
        client_id=client.id,
        agency_id=client.agency_id,
        agency_name=getattr(agency, "agency_name", None),
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


def _warehouse_summary(warehouse) -> WarehouseSummary:
    return WarehouseSummary(
        warehouse_id=warehouse.id,
        warehouse_code=warehouse.warehouse_code,
        warehouse_name=warehouse.warehouse_name,
        warehouse_type=warehouse.warehouse_type,
        active_yn=warehouse.active_yn,
    )


def _client_warehouse_setting_response(db: Session, auth: AuthContext, setting) -> dict:
    client = repo.get_client(db, setting.client_id)
    warehouse = repo.get_warehouse_by_id(db, setting.warehouse_id)
    if client is None:
        raise _business_error("MASTER_CLIENT_NOT_FOUND", "Client not found.", 404)
    if warehouse is None:
        raise _business_error("MASTER_WAREHOUSE_NOT_FOUND", "Warehouse not found.", 404)
    return _dump(
        ClientWarehouseSettingResponse(
            setting_id=setting.id,
            agency_id=setting.agency_id,
            client_id=client.id,
            client_code=client.client_code,
            client_name=client.client_name,
            warehouse_id=warehouse.id,
            warehouse_code=warehouse.warehouse_code,
            warehouse_name=warehouse.warehouse_name,
            warehouse_type=warehouse.warehouse_type,
            warehouse_active_yn=warehouse.active_yn,
            usage_type=setting.usage_type,
            usage_type_label=_usage_type_label(setting.usage_type),
            is_default=setting.is_default,
            active_yn=setting.active_yn,
            allowed_actions=_client_warehouse_allowed_actions(auth, setting, warehouse),
            created_at=setting.created_at,
            updated_at=setting.updated_at,
        )
    )


def _client_unit_response(unit, client, default_warehouse=None, return_warehouse=None) -> dict:
    return _dump(
        ClientUnitResponse(
            unit_id=unit.id,
            agency_id=unit.agency_id,
            client_id=client.id,
            client_code=client.client_code,
            client_name=client.client_name,
            unit_code=unit.unit_code,
            unit_name=unit.unit_name,
            unit_type=unit.unit_type,
            default_warehouse_id=unit.default_warehouse_id,
            default_warehouse_name=default_warehouse.warehouse_name if default_warehouse else None,
            return_warehouse_id=unit.return_warehouse_id,
            return_warehouse_name=return_warehouse.warehouse_name if return_warehouse else None,
            active_yn=unit.active_yn,
            sort_order=unit.sort_order,
            memo=unit.memo,
            created_at=unit.created_at,
            updated_at=unit.updated_at,
        )
    )


def _client_unit_response_by_id(db: Session, unit_id: int) -> dict:
    row = repo.get_client_unit_with_client(db, unit_id)
    if row is None:
        raise _business_error("MASTER_CLIENT_UNIT_NOT_FOUND", "고객사 운영단위를 찾을 수 없습니다.", 404)
    unit, client = row
    default_warehouse = repo.get_warehouse_by_id(db, unit.default_warehouse_id) if unit.default_warehouse_id else None
    return_warehouse = repo.get_warehouse_by_id(db, unit.return_warehouse_id) if unit.return_warehouse_id else None
    return _client_unit_response(unit, client, default_warehouse, return_warehouse)


def _return_warehouse_route_response(route, client, client_unit=None, warehouse=None) -> dict:
    return _dump(
        ReturnJudgmentWarehouseRouteResponse(
            route_id=route.id,
            agency_id=route.agency_id,
            client_id=route.client_id,
            client_code=client.client_code if client else None,
            client_name=client.client_name if client else None,
            client_unit_id=route.client_unit_id,
            client_unit_name=client_unit.unit_name if client_unit else None,
            judgment_code=route.judgment_code,
            warehouse_id=route.warehouse_id,
            warehouse_code=warehouse.warehouse_code if warehouse else None,
            warehouse_name=warehouse.warehouse_name if warehouse else None,
            active_yn=route.active_yn,
            sort_order=route.sort_order,
            memo=route.memo,
            created_at=route.created_at,
            updated_at=route.updated_at,
        )
    )


def _return_warehouse_route_response_by_id(db: Session, route_id: int) -> dict:
    row = repo.get_return_judgment_warehouse_route_with_client(db, route_id)
    if row is None:
        raise _business_error("MASTER_RETURN_WAREHOUSE_ROUTE_NOT_FOUND", "판정별 창고 라우팅을 찾을 수 없습니다.", 404)
    route, client = row
    unit = repo.get_client_unit_by_id(db, route.client_unit_id) if route.client_unit_id else None
    warehouse = repo.get_warehouse_by_id(db, route.warehouse_id)
    return _return_warehouse_route_response(route, client, unit, warehouse)


def _common_code_group_summary(group) -> dict:
    return _dump(
        CommonCodeGroupSummary(
            group_id=group.id,
            group_code=group.group_code,
            group_name=group.group_name,
            active_yn=group.active_yn,
        )
    )


def _common_code_summary(code, group) -> dict:
    return _dump(
        CommonCodeSummary(
            code_id=code.id,
            group_code=group.group_code,
            code_value=code.code_value,
            code_name=code.code_name,
            sort_order=code.sort_order,
            active_yn=code.active_yn,
        )
    )


def _common_code_summary_by_id(db: Session, code_id: int) -> dict:
    code = repo.get_common_code_by_id(db, code_id)
    if code is None:
        raise _business_error("MASTER_COMMON_CODE_NOT_FOUND", "怨듯넻肄붾뱶瑜?李얠쓣 ???놁뒿?덈떎.", 404)
    group = repo.get_common_code_group_by_id(db, code.group_id)
    if group is None:
        raise _business_error("MASTER_COMMON_CODE_GROUP_NOT_FOUND", "怨듯넻肄붾뱶 洹몃９??李얠쓣 ???놁뒿?덈떎.", 404)
    return _common_code_summary(code, group)


def _ensure_common_code_group_code_available(db: Session, group_code: str) -> None:
    if repo.find_common_code_group_by_code(db, group_code):
        raise _business_error("MASTER_COMMON_CODE_GROUP_DUPLICATED", "?대? ?깅줉??怨듯넻肄붾뱶 洹몃９?낅땲??")


def _ensure_common_code_value_available(db: Session, group_id: int, code_value: str) -> None:
    if repo.find_common_code_by_value(db, group_id, code_value):
        raise _business_error("MASTER_COMMON_CODE_DUPLICATED", "?대? ?깅줉??怨듯넻肄붾뱶媛믪엯?덈떎.")


def get_accessible_clients(db: Session, auth: AuthContext) -> list[dict]:
    if auth.is_internal_user:
        return [_dump(_client_summary(client)) for client in repo.list_clients(db)]
    if auth.is_agency_user and auth.agency_id is not None:
        return [_dump(_client_summary(client)) for client in repo.list_clients(db, agency_id=auth.agency_id)]
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


def create_client(db: Session, auth: AuthContext, request: ClientCreateRequest) -> dict:
    _require_client_manage(auth)
    _ensure_client_code_available(db, request.client_code)
    agency_id = resolve_effective_agency_id(auth, auth.agency_id, allow_all_agencies=False)
    if agency_id is None:
        default_agency = repo.get_default_agency(db)
        agency_id = default_agency.id if default_agency is not None else None

    try:
        client = repo.create_client(
            db,
            agency_id=agency_id,
            client_code=request.client_code,
            client_name=request.client_name,
            business_no=request.business_no,
            contact_name=request.contact_name,
            contact_phone=request.contact_phone,
            contact_email=request.contact_email,
            use_oms=request.use_oms,
            use_wms=request.use_wms,
            use_returns=request.use_returns,
            use_settlement=request.use_settlement,
            remarks=request.remarks,
        )
        db.commit()
        return _dump(_client_detail(client))
    except Exception:
        db.rollback()
        raise


def update_client(db: Session, auth: AuthContext, client_id: int, request: ClientUpdateRequest) -> dict:
    _require_client_manage(auth)
    client = repo.get_client_by_id(db, client_id)
    if client is None:
        raise _business_error("MASTER_CLIENT_NOT_FOUND", "고객사를 찾을 수 없습니다.", 404)

    try:
        repo.update_client(db, client, request.model_dump(exclude_unset=True))
        db.commit()
        return _dump(_client_detail(client))
    except Exception:
        db.rollback()
        raise


def set_client_active(db: Session, auth: AuthContext, client_id: int, active_yn: bool) -> dict:
    _require_client_manage(auth)
    client = repo.get_client_by_id(db, client_id)
    if client is None:
        raise _business_error("MASTER_CLIENT_NOT_FOUND", "고객사를 찾을 수 없습니다.", 404)

    try:
        repo.set_client_active(db, client, active_yn)
        db.commit()
        return _dump(_client_detail(client))
    except Exception:
        db.rollback()
        raise


def _ensure_optional_active_warehouse(db: Session, warehouse_id: int | None):
    if warehouse_id is None:
        return None
    return _ensure_active_warehouse(db, warehouse_id)


def _ensure_optional_client_warehouse(db: Session, client_id: int, warehouse_id: int | None):
    if warehouse_id is None:
        return None
    warehouse = _ensure_active_warehouse(db, warehouse_id)
    setting = repo.find_active_client_warehouse_for_warehouse(db, client_id=client_id, warehouse_id=warehouse_id)
    if setting is None:
        raise _business_error("MASTER_CLIENT_UNIT_WAREHOUSE_UNLINKED", "고객사에 연결된 활성 창고만 운영단위 창고로 사용할 수 있습니다.")
    return warehouse


def _ensure_return_warehouse_route_judgment_code(judgment_code: str) -> str:
    judgment_code = judgment_code.strip().upper()
    if judgment_code not in RETURN_WAREHOUSE_ROUTE_JUDGMENT_CODES:
        raise _business_error("MASTER_RETURN_WAREHOUSE_ROUTE_JUDGMENT_INVALID", "지원하지 않는 판정 코드입니다.")
    return judgment_code


def _ensure_route_client_unit(db: Session, client_id: int, client_unit_id: int | None):
    if client_unit_id is None:
        return None
    unit = repo.get_client_unit_by_id(db, client_unit_id)
    if unit is None or unit.client_id != client_id:
        raise _business_error("MASTER_RETURN_WAREHOUSE_ROUTE_UNIT_INVALID", "고객사 운영단위를 확인할 수 없습니다.", 404)
    if not unit.active_yn:
        raise _business_error("MASTER_RETURN_WAREHOUSE_ROUTE_UNIT_INACTIVE", "사용중지된 운영단위는 라우팅에 연결할 수 없습니다.")
    return unit


def _ensure_route_warehouse(db: Session, client_id: int, warehouse_id: int):
    warehouse = _ensure_active_warehouse(db, warehouse_id)
    setting = repo.find_active_client_warehouse_for_warehouse(db, client_id=client_id, warehouse_id=warehouse_id)
    if setting is None:
        raise _business_error("MASTER_RETURN_WAREHOUSE_ROUTE_WAREHOUSE_UNLINKED", "고객사에 연결된 활성 창고만 라우팅에 사용할 수 있습니다.")
    return warehouse


def _ensure_return_warehouse_route_available(
    db: Session,
    *,
    client_id: int,
    client_unit_id: int | None,
    judgment_code: str,
    exclude_route_id: int | None = None,
) -> None:
    existing = repo.find_duplicate_return_judgment_warehouse_route(
        db,
        client_id=client_id,
        client_unit_id=client_unit_id,
        judgment_code=judgment_code,
        exclude_route_id=exclude_route_id,
    )
    if existing is not None:
        raise _business_error("MASTER_RETURN_WAREHOUSE_ROUTE_DUPLICATED", "이미 활성화된 판정별 창고 라우팅이 있습니다.")


def _ensure_client_unit_code_available(
    db: Session,
    *,
    client_id: int,
    unit_code: str,
    exclude_unit_id: int | None = None,
) -> None:
    existing = repo.find_client_unit_by_code(db, client_id=client_id, unit_code=unit_code)
    if existing is not None and existing.id != exclude_unit_id:
        raise _business_error("MASTER_CLIENT_UNIT_CODE_DUPLICATED", "이미 등록된 고객사 운영단위 코드입니다.")


def get_client_units_for_client(
    db: Session,
    auth: AuthContext,
    client_id: int,
    *,
    include_inactive: bool = False,
) -> list[dict]:
    effective_client_id = resolve_effective_client_id(auth, client_id)
    client = repo.get_client_by_id(db, effective_client_id)
    if client is None:
        raise _business_error("MASTER_CLIENT_NOT_FOUND", "고객사를 찾을 수 없습니다.", 404)
    active_only = not include_inactive or auth.is_client_user
    rows = repo.list_client_units(db, client_id=effective_client_id, active_only=active_only)
    return [_client_unit_response(unit, client, default_warehouse, return_warehouse) for unit, client, default_warehouse, return_warehouse in rows]


def create_client_unit_for_client(
    db: Session,
    auth: AuthContext,
    client_id: int,
    request: ClientUnitCreateRequest,
) -> dict:
    _require_client_manage(auth)
    effective_client_id = resolve_effective_client_id(auth, client_id)
    _ensure_active_client(db, effective_client_id)
    _ensure_client_unit_code_available(db, client_id=effective_client_id, unit_code=request.unit_code)
    _ensure_optional_client_warehouse(db, effective_client_id, request.default_warehouse_id)
    _ensure_optional_client_warehouse(db, effective_client_id, request.return_warehouse_id)
    try:
        unit = repo.create_client_unit(db, client_id=effective_client_id, **request.model_dump())
        db.commit()
        return _client_unit_response_by_id(db, unit.id)
    except Exception:
        db.rollback()
        raise


def update_client_unit_for_client(
    db: Session,
    auth: AuthContext,
    client_id: int,
    unit_id: int,
    request: ClientUnitUpdateRequest,
) -> dict:
    _require_client_manage(auth)
    effective_client_id = resolve_effective_client_id(auth, client_id)
    row = repo.get_client_unit_with_client(db, unit_id)
    if row is None:
        raise _business_error("MASTER_CLIENT_UNIT_NOT_FOUND", "고객사 운영단위를 찾을 수 없습니다.", 404)
    unit, _client = row
    if unit.client_id != effective_client_id:
        raise ClientScopeDeniedError("다른 고객사의 운영단위는 수정할 수 없습니다.")
    values = request.model_dump(exclude_unset=True)
    if "unit_code" in values and values["unit_code"] is not None:
        _ensure_client_unit_code_available(
            db,
            client_id=effective_client_id,
            unit_code=str(values["unit_code"]),
            exclude_unit_id=unit.id,
        )
    if "default_warehouse_id" in values:
        _ensure_optional_client_warehouse(db, effective_client_id, values["default_warehouse_id"])
    if "return_warehouse_id" in values:
        _ensure_optional_client_warehouse(db, effective_client_id, values["return_warehouse_id"])
    try:
        repo.update_client_unit(db, unit, values)
        db.commit()
        return _client_unit_response_by_id(db, unit.id)
    except Exception:
        db.rollback()
        raise


def set_client_unit_active_for_client(
    db: Session,
    auth: AuthContext,
    client_id: int,
    unit_id: int,
    active_yn: bool,
) -> dict:
    _require_client_manage(auth)
    effective_client_id = resolve_effective_client_id(auth, client_id)
    row = repo.get_client_unit_with_client(db, unit_id)
    if row is None:
        raise _business_error("MASTER_CLIENT_UNIT_NOT_FOUND", "고객사 운영단위를 찾을 수 없습니다.", 404)
    unit, _client = row
    if unit.client_id != effective_client_id:
        raise ClientScopeDeniedError("다른 고객사의 운영단위는 변경할 수 없습니다.")
    if active_yn:
        _ensure_active_client(db, effective_client_id)
        _ensure_optional_client_warehouse(db, effective_client_id, unit.default_warehouse_id)
        _ensure_optional_client_warehouse(db, effective_client_id, unit.return_warehouse_id)
    try:
        repo.set_client_unit_active(db, unit, active_yn)
        db.commit()
        return _client_unit_response_by_id(db, unit.id)
    except Exception:
        db.rollback()
        raise


def get_return_warehouse_routes_for_client(
    db: Session,
    auth: AuthContext,
    client_id: int,
    *,
    include_inactive: bool = False,
) -> list[dict]:
    effective_client_id = resolve_effective_client_id(auth, client_id)
    client = repo.get_client_by_id(db, effective_client_id)
    if client is None:
        raise _business_error("MASTER_CLIENT_NOT_FOUND", "고객사를 찾을 수 없습니다.", 404)
    active_only = not include_inactive or auth.is_client_user
    rows = repo.list_return_judgment_warehouse_routes(db, client_id=effective_client_id, active_only=active_only)
    return [_return_warehouse_route_response(route, client, unit, warehouse) for route, client, unit, warehouse in rows]


def create_return_warehouse_route_for_client(
    db: Session,
    auth: AuthContext,
    client_id: int,
    request: ReturnJudgmentWarehouseRouteCreateRequest,
) -> dict:
    _require_warehouse_manage(auth)
    effective_client_id = resolve_effective_client_id(auth, client_id)
    _ensure_active_client(db, effective_client_id)
    judgment_code = _ensure_return_warehouse_route_judgment_code(request.judgment_code)
    unit = _ensure_route_client_unit(db, effective_client_id, request.client_unit_id)
    _ensure_route_warehouse(db, effective_client_id, request.warehouse_id)
    _ensure_return_warehouse_route_available(
        db,
        client_id=effective_client_id,
        client_unit_id=unit.id if unit else None,
        judgment_code=judgment_code,
    )
    try:
        route = repo.create_return_judgment_warehouse_route(
            db,
            client_id=effective_client_id,
            client_unit_id=unit.id if unit else None,
            judgment_code=judgment_code,
            warehouse_id=request.warehouse_id,
            sort_order=request.sort_order,
            memo=request.memo,
        )
        db.commit()
        return _return_warehouse_route_response_by_id(db, route.id)
    except Exception:
        db.rollback()
        raise


def update_return_warehouse_route_for_client(
    db: Session,
    auth: AuthContext,
    client_id: int,
    route_id: int,
    request: ReturnJudgmentWarehouseRouteUpdateRequest,
) -> dict:
    _require_warehouse_manage(auth)
    effective_client_id = resolve_effective_client_id(auth, client_id)
    row = repo.get_return_judgment_warehouse_route_with_client(db, route_id)
    if row is None:
        raise _business_error("MASTER_RETURN_WAREHOUSE_ROUTE_NOT_FOUND", "판정별 창고 라우팅을 찾을 수 없습니다.", 404)
    route, _client = row
    if route.client_id != effective_client_id:
        raise ClientScopeDeniedError("다른 고객사의 판정별 창고 라우팅은 수정할 수 없습니다.")
    values = request.model_dump(exclude_unset=True)
    next_judgment_code = route.judgment_code
    if "judgment_code" in values and values["judgment_code"] is not None:
        next_judgment_code = _ensure_return_warehouse_route_judgment_code(str(values["judgment_code"]))
        values["judgment_code"] = next_judgment_code
    next_client_unit_id = route.client_unit_id
    if "client_unit_id" in values:
        unit = _ensure_route_client_unit(db, effective_client_id, values["client_unit_id"])
        next_client_unit_id = unit.id if unit else None
        values["client_unit_id"] = next_client_unit_id
    if "warehouse_id" in values and values["warehouse_id"] is not None:
        _ensure_route_warehouse(db, effective_client_id, int(values["warehouse_id"]))
    if route.active_yn:
        _ensure_return_warehouse_route_available(
            db,
            client_id=effective_client_id,
            client_unit_id=next_client_unit_id,
            judgment_code=next_judgment_code,
            exclude_route_id=route.id,
        )
    try:
        repo.update_return_judgment_warehouse_route(db, route, values)
        db.commit()
        return _return_warehouse_route_response_by_id(db, route.id)
    except Exception:
        db.rollback()
        raise


def set_return_warehouse_route_active_for_client(
    db: Session,
    auth: AuthContext,
    client_id: int,
    route_id: int,
    active_yn: bool,
) -> dict:
    _require_warehouse_manage(auth)
    effective_client_id = resolve_effective_client_id(auth, client_id)
    row = repo.get_return_judgment_warehouse_route_with_client(db, route_id)
    if row is None:
        raise _business_error("MASTER_RETURN_WAREHOUSE_ROUTE_NOT_FOUND", "판정별 창고 라우팅을 찾을 수 없습니다.", 404)
    route, _client = row
    if route.client_id != effective_client_id:
        raise ClientScopeDeniedError("다른 고객사의 판정별 창고 라우팅은 변경할 수 없습니다.")
    if active_yn:
        _ensure_active_client(db, effective_client_id)
        _ensure_route_client_unit(db, effective_client_id, route.client_unit_id)
        _ensure_route_warehouse(db, effective_client_id, route.warehouse_id)
        _ensure_return_warehouse_route_available(
            db,
            client_id=effective_client_id,
            client_unit_id=route.client_unit_id,
            judgment_code=route.judgment_code,
            exclude_route_id=route.id,
        )
    try:
        repo.set_return_judgment_warehouse_route_active(db, route, active_yn)
        db.commit()
        return _return_warehouse_route_response_by_id(db, route.id)
    except Exception:
        db.rollback()
        raise


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


def create_warehouse(db: Session, auth: AuthContext, request: WarehouseCreateRequest) -> dict:
    _require_warehouse_manage(auth)
    _ensure_warehouse_code_available(db, request.warehouse_code)

    try:
        warehouse = repo.create_warehouse(
            db,
            warehouse_code=request.warehouse_code,
            warehouse_name=request.warehouse_name,
            warehouse_type=request.warehouse_type,
            address=request.address,
            remarks=request.remarks,
        )
        db.commit()
        return _dump(_warehouse_summary(warehouse))
    except Exception:
        db.rollback()
        raise


def update_warehouse(
    db: Session,
    auth: AuthContext,
    warehouse_id: int,
    request: WarehouseUpdateRequest,
) -> dict:
    _require_warehouse_manage(auth)
    warehouse = repo.get_warehouse_by_id(db, warehouse_id)
    if warehouse is None:
        raise _business_error("MASTER_WAREHOUSE_NOT_FOUND", "창고를 찾을 수 없습니다.", 404)

    try:
        repo.update_warehouse(db, warehouse, request.model_dump(exclude_unset=True))
        db.commit()
        return _dump(_warehouse_summary(warehouse))
    except Exception:
        db.rollback()
        raise


def set_warehouse_active(db: Session, auth: AuthContext, warehouse_id: int, active_yn: bool) -> dict:
    _require_warehouse_manage(auth)
    warehouse = repo.get_warehouse_by_id(db, warehouse_id)
    if warehouse is None:
        raise _business_error("MASTER_WAREHOUSE_NOT_FOUND", "창고를 찾을 수 없습니다.", 404)

    try:
        repo.set_warehouse_active(db, warehouse, active_yn)
        db.commit()
        return _dump(_warehouse_summary(warehouse))
    except Exception:
        db.rollback()
        raise


def get_client_warehouses(
    db: Session,
    auth: AuthContext,
    client_id: int | None = None,
    *,
    include_inactive: bool = False,
) -> list[dict]:
    effective_client_id = resolve_effective_client_id(auth, client_id)
    if effective_client_id is None:
        raise ClientScopeDeniedError("고객사 창고 조회에는 client_id가 필요합니다.")

    active_only = True if auth.is_client_user else not include_inactive
    rows = repo.list_client_warehouses(db, effective_client_id, active_only=active_only)
    return [
        _dump(
            ClientWarehouseSummary(
                setting_id=setting.id,
                client_id=client.id,
                client_code=client.client_code,
                client_name=client.client_name,
                warehouse_id=warehouse.id,
                warehouse_code=warehouse.warehouse_code,
                warehouse_name=warehouse.warehouse_name,
                warehouse_type=warehouse.warehouse_type,
                warehouse_active_yn=warehouse.active_yn,
                usage_type=setting.usage_type,
                usage_type_label=_usage_type_label(setting.usage_type),
                is_default=setting.is_default,
                active_yn=setting.active_yn,
                allowed_actions=_client_warehouse_allowed_actions(auth, setting, warehouse),
                created_at=setting.created_at,
                updated_at=setting.updated_at,
            )
        )
        for setting, client, warehouse in rows
    ]


def get_client_warehouse_settings_for_client(
    db: Session,
    auth: AuthContext,
    client_id: int,
    *,
    include_inactive: bool = False,
) -> list[dict]:
    resolve_effective_client_id(auth, client_id)
    if repo.get_client(db, client_id) is None:
        raise _business_error("MASTER_CLIENT_NOT_FOUND", "고객사를 찾을 수 없습니다.", 404)
    return get_client_warehouses(db, auth, client_id, include_inactive=include_inactive)


def get_client_warehouse_options(
    db: Session,
    auth: AuthContext,
    client_id: int,
    *,
    include_inactive: bool = False,
) -> list[dict]:
    _require_warehouse_manage(auth)
    _ensure_active_client(db, client_id)
    linked_settings = repo.list_client_warehouse_settings_only(db, client_id, active_only=False)
    linked_by_warehouse: dict[int, list] = {}
    for setting in linked_settings:
        linked_by_warehouse.setdefault(setting.warehouse_id, []).append(setting)

    return [
        _dump(
            WarehouseOptionResponse(
                warehouse_id=warehouse.id,
                warehouse_code=warehouse.warehouse_code,
                warehouse_name=warehouse.warehouse_name,
                warehouse_type=warehouse.warehouse_type,
                active_yn=warehouse.active_yn,
                already_linked=bool([s for s in linked_by_warehouse.get(warehouse.id, []) if s.active_yn]),
                linked_usage_types=sorted(
                    {s.usage_type for s in linked_by_warehouse.get(warehouse.id, []) if s.active_yn}
                ),
                default_usage_types=sorted(
                    {
                        s.usage_type
                        for s in linked_by_warehouse.get(warehouse.id, [])
                        if s.active_yn and s.is_default
                    }
                ),
            )
        )
        for warehouse in repo.list_warehouses(db, active_only=not include_inactive)
    ]


def _ensure_client_warehouse_setting_for_client(db: Session, client_id: int, setting_id: int):
    setting = repo.get_client_warehouse_setting_by_id(db, setting_id)
    if setting is None or setting.client_id != client_id:
        raise _business_error("MASTER_CLIENT_WAREHOUSE_NOT_FOUND", "Client warehouse setting not found.", 404)
    return setting


def create_client_warehouse_setting_for_client(
    db: Session,
    auth: AuthContext,
    client_id: int,
    request: ClientWarehouseSettingNestedCreateRequest,
) -> dict:
    _require_warehouse_manage(auth)
    resolve_effective_client_id(auth, client_id)
    return create_client_warehouse_setting(
        db,
        auth,
        ClientWarehouseSettingCreateRequest(
            client_id=client_id,
            warehouse_id=request.warehouse_id,
            usage_type=request.usage_type,
            is_default=request.is_default,
        ),
    )


def update_client_warehouse_setting_for_client(
    db: Session,
    auth: AuthContext,
    client_id: int,
    setting_id: int,
    request: ClientWarehouseSettingUpdateRequest,
) -> dict:
    _require_warehouse_manage(auth)
    resolve_effective_client_id(auth, client_id)
    _ensure_client_warehouse_setting_for_client(db, client_id, setting_id)
    return update_client_warehouse_setting(db, auth, setting_id, request)


def set_client_warehouse_setting_active_for_client(
    db: Session,
    auth: AuthContext,
    client_id: int,
    setting_id: int,
    active_yn: bool,
) -> dict:
    _require_warehouse_manage(auth)
    resolve_effective_client_id(auth, client_id)
    _ensure_client_warehouse_setting_for_client(db, client_id, setting_id)
    return set_client_warehouse_setting_active(db, auth, setting_id, active_yn)


def set_default_client_warehouse_setting_for_client(
    db: Session,
    auth: AuthContext,
    client_id: int,
    setting_id: int,
) -> dict:
    _require_warehouse_manage(auth)
    resolve_effective_client_id(auth, client_id)
    _ensure_client_warehouse_setting_for_client(db, client_id, setting_id)
    return set_default_client_warehouse_setting(db, auth, setting_id)


def create_client_warehouse_setting(
    db: Session,
    auth: AuthContext,
    request: ClientWarehouseSettingCreateRequest,
) -> dict:
    _require_warehouse_manage(auth)
    _ensure_active_client(db, request.client_id)
    _ensure_active_warehouse(db, request.warehouse_id)
    usage_type = _ensure_client_warehouse_usage_type(request.usage_type)
    _ensure_client_warehouse_setting_available(
        db,
        client_id=request.client_id,
        warehouse_id=request.warehouse_id,
        usage_type=usage_type,
    )

    try:
        if request.is_default:
            repo.unset_default_client_warehouse_settings(db, client_id=request.client_id, usage_type=usage_type)
        setting = repo.create_client_warehouse_setting(
            db,
            client_id=request.client_id,
            warehouse_id=request.warehouse_id,
            usage_type=usage_type,
            is_default=request.is_default,
        )
        db.commit()
        return _client_warehouse_setting_response(db, auth, setting)
    except Exception:
        db.rollback()
        raise


def update_client_warehouse_setting(
    db: Session,
    auth: AuthContext,
    setting_id: int,
    request: ClientWarehouseSettingUpdateRequest,
) -> dict:
    _require_warehouse_manage(auth)
    setting = repo.get_client_warehouse_setting_by_id(db, setting_id)
    if setting is None:
        raise _business_error("MASTER_CLIENT_WAREHOUSE_NOT_FOUND", "Client warehouse setting not found.", 404)

    values = request.model_dump(exclude_unset=True)
    if "usage_type" in values:
        usage_type = _ensure_client_warehouse_usage_type(str(values["usage_type"]))
        if setting.is_default and usage_type != setting.usage_type:
            raise _business_error(
                "MASTER_CLIENT_WAREHOUSE_DEFAULT_USAGE_TYPE_LOCKED",
                "Default client warehouse usage_type cannot be changed.",
            )
        if usage_type != setting.usage_type:
            _ensure_client_warehouse_setting_available(
                db,
                client_id=setting.client_id,
                warehouse_id=setting.warehouse_id,
                usage_type=usage_type,
                exclude_setting_id=setting.id,
            )
        values["usage_type"] = usage_type

    try:
        repo.update_client_warehouse_setting(db, setting, values)
        db.commit()
        return _client_warehouse_setting_response(db, auth, setting)
    except Exception:
        db.rollback()
        raise


def set_client_warehouse_setting_active(
    db: Session,
    auth: AuthContext,
    setting_id: int,
    active_yn: bool,
) -> dict:
    _require_warehouse_manage(auth)
    setting = repo.get_client_warehouse_setting_by_id(db, setting_id)
    if setting is None:
        raise _business_error("MASTER_CLIENT_WAREHOUSE_NOT_FOUND", "Client warehouse setting not found.", 404)
    if not active_yn and setting.is_default:
        raise _business_error(
            "MASTER_CLIENT_WAREHOUSE_DEFAULT_DISABLE_DENIED",
            "Default client warehouse setting cannot be disabled.",
        )
    if active_yn:
        _ensure_active_client(db, setting.client_id)
        _ensure_active_warehouse(db, setting.warehouse_id)

    try:
        repo.set_client_warehouse_setting_active(db, setting, active_yn)
        db.commit()
        return _client_warehouse_setting_response(db, auth, setting)
    except Exception:
        db.rollback()
        raise


def set_default_client_warehouse_setting(db: Session, auth: AuthContext, setting_id: int) -> dict:
    _require_warehouse_manage(auth)
    setting = repo.get_client_warehouse_setting_by_id(db, setting_id)
    if setting is None:
        raise _business_error("MASTER_CLIENT_WAREHOUSE_NOT_FOUND", "Client warehouse setting not found.", 404)
    if not setting.active_yn:
        raise _business_error("MASTER_CLIENT_WAREHOUSE_INACTIVE", "Inactive setting cannot become default.")
    _ensure_active_client(db, setting.client_id)
    _ensure_active_warehouse(db, setting.warehouse_id)

    try:
        repo.unset_default_client_warehouse_settings(db, client_id=setting.client_id, usage_type=setting.usage_type)
        repo.set_client_warehouse_setting_default(db, setting)
        db.commit()
        return _client_warehouse_setting_response(db, auth, setting)
    except Exception:
        db.rollback()
        raise


def get_products(
    db: Session,
    auth: AuthContext,
    client_id: int | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    effective_client_id = resolve_effective_client_id(auth, client_id, allow_all_clients=True)
    effective_agency_id = resolve_effective_agency_id(auth, None, allow_all_agencies=True)
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 200)
    rows, total_count = repo.list_products(
        db,
        agency_id=effective_agency_id,
        client_id=effective_client_id,
        keyword=keyword,
        page=safe_page,
        page_size=safe_page_size,
    )
    items = [
        _dump(
            ProductSummary(
                product_id=product.id,
                agency_id=product.agency_id,
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
            agency_id=barcode.agency_id,
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
            agency_id=product.agency_id,
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
    return [_common_code_group_summary(group) for group in repo.list_common_code_groups(db)]


def get_common_codes(db: Session, auth: AuthContext, group_code: str | None = None) -> list[dict]:
    return [_common_code_summary(code, group) for code, group in repo.list_common_codes(db, group_code=group_code)]


def create_common_code_group(
    db: Session,
    auth: AuthContext,
    request: CommonCodeGroupCreateRequest,
) -> dict:
    _require_common_code_manage(auth)
    _ensure_common_code_group_code_available(db, request.group_code)

    try:
        group = repo.create_common_code_group(
            db,
            group_code=request.group_code,
            group_name=request.group_name,
            description=request.description,
        )
        db.commit()
        return _common_code_group_summary(group)
    except Exception:
        db.rollback()
        raise


def update_common_code_group(
    db: Session,
    auth: AuthContext,
    group_id: int,
    request: CommonCodeGroupUpdateRequest,
) -> dict:
    _require_common_code_manage(auth)
    group = repo.get_common_code_group_by_id(db, group_id)
    if group is None:
        raise _business_error("MASTER_COMMON_CODE_GROUP_NOT_FOUND", "怨듯넻肄붾뱶 洹몃９??李얠쓣 ???놁뒿?덈떎.", 404)

    try:
        repo.update_common_code_group(db, group, request.model_dump(exclude_unset=True))
        db.commit()
        return _common_code_group_summary(group)
    except Exception:
        db.rollback()
        raise


def set_common_code_group_active(db: Session, auth: AuthContext, group_id: int, active_yn: bool) -> dict:
    _require_common_code_manage(auth)
    group = repo.get_common_code_group_by_id(db, group_id)
    if group is None:
        raise _business_error("MASTER_COMMON_CODE_GROUP_NOT_FOUND", "怨듯넻肄붾뱶 洹몃９??李얠쓣 ???놁뒿?덈떎.", 404)

    try:
        repo.set_common_code_group_active(db, group, active_yn)
        db.commit()
        return _common_code_group_summary(group)
    except Exception:
        db.rollback()
        raise


def create_common_code(db: Session, auth: AuthContext, request: CommonCodeCreateRequest) -> dict:
    _require_common_code_manage(auth)
    group = repo.get_common_code_group_by_id(db, request.group_id)
    if group is None:
        raise _business_error("MASTER_COMMON_CODE_GROUP_NOT_FOUND", "怨듯넻肄붾뱶 洹몃９??李얠쓣 ???놁뒿?덈떎.", 404)
    if not group.active_yn:
        raise _business_error("MASTER_COMMON_CODE_GROUP_INACTIVE", "?ъ슜以묒???怨듯넻肄붾뱶 洹몃９?먮뒗 肄붾뱶瑜??앹꽦?????놁뒿?덈떎.")
    _ensure_common_code_value_available(db, request.group_id, request.code_value)

    try:
        code = repo.create_common_code(
            db,
            group_id=request.group_id,
            code_value=request.code_value,
            code_name=request.code_name,
            sort_order=request.sort_order,
            description=request.description,
        )
        db.commit()
        return _common_code_summary(code, group)
    except Exception:
        db.rollback()
        raise


def update_common_code(db: Session, auth: AuthContext, code_id: int, request: CommonCodeUpdateRequest) -> dict:
    _require_common_code_manage(auth)
    code = repo.get_common_code_by_id(db, code_id)
    if code is None:
        raise _business_error("MASTER_COMMON_CODE_NOT_FOUND", "怨듯넻肄붾뱶瑜?李얠쓣 ???놁뒿?덈떎.", 404)
    if code.locked_yn:
        raise _business_error("MASTER_COMMON_CODE_LOCKED", "잠긴 공통코드는 수정할 수 없습니다.")

    try:
        repo.update_common_code(db, code, request.model_dump(exclude_unset=True))
        db.commit()
        return _common_code_summary_by_id(db, code.id)
    except Exception:
        db.rollback()
        raise


def set_common_code_active(db: Session, auth: AuthContext, code_id: int, active_yn: bool) -> dict:
    _require_common_code_manage(auth)
    code = repo.get_common_code_by_id(db, code_id)
    if code is None:
        raise _business_error("MASTER_COMMON_CODE_NOT_FOUND", "怨듯넻肄붾뱶瑜?李얠쓣 ???놁뒿?덈떎.", 404)
    if not active_yn and (code.system_yn or code.locked_yn):
        raise _business_error("MASTER_COMMON_CODE_LOCKED", "시스템 또는 잠긴 공통코드는 사용중지할 수 없습니다.")

    try:
        repo.set_common_code_active(db, code, active_yn)
        db.commit()
        return _common_code_summary_by_id(db, code.id)
    except Exception:
        db.rollback()
        raise
