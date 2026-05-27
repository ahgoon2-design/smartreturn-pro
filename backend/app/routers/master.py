"""P0 기준정보 read-only API skeleton."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_auth_context, get_db
from app.core.permissions import require_password_change_completed, require_permission, require_roles
from app.schemas.auth import AuthContext
from app.schemas.common import ApiResult, api_success
from app.services import master_service


router = APIRouter(prefix="/api/master", tags=["master"])


def _require_master_view(auth: AuthContext) -> None:
    require_password_change_completed(auth)
    require_permission(auth, "MASTER_VIEW")


@router.get("/clients", response_model=ApiResult)
def list_clients_api(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_master_view(auth)
    return api_success(
        result_code="MASTER_CLIENTS_FOUND",
        message="고객사 목록을 조회했습니다.",
        data=master_service.get_accessible_clients(db, auth),
    )


@router.get("/clients/{client_id}", response_model=ApiResult)
def get_client_api(
    client_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_master_view(auth)
    return api_success(
        result_code="MASTER_CLIENT_FOUND",
        message="고객사 상세를 조회했습니다.",
        data=master_service.get_client_detail(db, auth, client_id),
    )


@router.get("/warehouses", response_model=ApiResult)
def list_warehouses_api(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_master_view(auth)
    require_roles(auth, {"SUPER_ADMIN", "INTERNAL_ADMIN"})
    return api_success(
        result_code="MASTER_WAREHOUSES_FOUND",
        message="창고 목록을 조회했습니다.",
        data=master_service.get_accessible_warehouses(db, auth),
    )


@router.get("/client-warehouses", response_model=ApiResult)
def list_client_warehouses_api(
    client_id: int | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_master_view(auth)
    return api_success(
        result_code="MASTER_CLIENT_WAREHOUSES_FOUND",
        message="고객사 사용창고 목록을 조회했습니다.",
        data=master_service.get_client_warehouses(db, auth, client_id),
    )


@router.get("/products", response_model=ApiResult)
def list_products_api(
    client_id: int | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_master_view(auth)
    return api_success(
        result_code="MASTER_PRODUCTS_FOUND",
        message="상품 목록을 조회했습니다.",
        data=master_service.get_products(db, auth, client_id, keyword, page, page_size),
    )


@router.get("/products/{product_id}", response_model=ApiResult)
def get_product_api(
    product_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_master_view(auth)
    return api_success(
        result_code="MASTER_PRODUCT_FOUND",
        message="상품 상세를 조회했습니다.",
        data=master_service.get_product_detail(db, auth, product_id),
    )


@router.get("/common-code-groups", response_model=ApiResult)
def list_common_code_groups_api(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_master_view(auth)
    return api_success(
        result_code="MASTER_COMMON_CODE_GROUPS_FOUND",
        message="공통코드 그룹 목록을 조회했습니다.",
        data=master_service.get_common_code_groups(db, auth),
    )


@router.get("/common-codes", response_model=ApiResult)
def list_common_codes_api(
    group_code: str | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_master_view(auth)
    return api_success(
        result_code="MASTER_COMMON_CODES_FOUND",
        message="공통코드 목록을 조회했습니다.",
        data=master_service.get_common_codes(db, auth, group_code),
    )
