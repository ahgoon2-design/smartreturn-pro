"""P0 기준정보 read-only API skeleton."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_auth_context, get_db
from app.core.permissions import require_password_change_completed, require_permission, require_roles
from app.schemas.auth import AuthContext
from app.schemas.common import ApiResult, api_success
from app.schemas.master import (
    CommonCodeCreateRequest,
    CommonCodeGroupCreateRequest,
    CommonCodeGroupUpdateRequest,
    CommonCodeUpdateRequest,
    ProductBarcodeCreateRequest,
    ProductBarcodeUpdateRequest,
    ProductCreateRequest,
    ProductUpdateRequest,
)
from app.services import master_service


router = APIRouter(prefix="/api/master", tags=["master"])


def _require_master_view(auth: AuthContext) -> None:
    require_password_change_completed(auth)
    require_permission(auth, "MASTER_VIEW")


def _require_product_manage(auth: AuthContext) -> None:
    require_password_change_completed(auth)
    require_roles(auth, {"SUPER_ADMIN", "INTERNAL_ADMIN", "INTERNAL_WORKER"})
    require_permission(auth, "MASTER_MANAGE")
    require_permission(auth, "PRODUCT_MANAGE")


def _require_common_code_manage(auth: AuthContext) -> None:
    require_password_change_completed(auth)
    require_roles(auth, {"SUPER_ADMIN", "INTERNAL_ADMIN"})
    require_permission(auth, "MASTER_MANAGE")
    require_permission(auth, "COMMON_CODE_MANAGE")


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


@router.post("/products", response_model=ApiResult)
def create_product_api(
    request: ProductCreateRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_product_manage(auth)
    return api_success(
        result_code="MASTER_PRODUCT_CREATED",
        message="상품을 생성했습니다.",
        data=master_service.create_product(db, auth, request),
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


@router.patch("/products/{product_id}", response_model=ApiResult)
def update_product_api(
    product_id: int,
    request: ProductUpdateRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_product_manage(auth)
    return api_success(
        result_code="MASTER_PRODUCT_UPDATED",
        message="상품을 수정했습니다.",
        data=master_service.update_product(db, auth, product_id, request),
    )


@router.post("/products/{product_id}/disable", response_model=ApiResult)
def disable_product_api(
    product_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_product_manage(auth)
    return api_success(
        result_code="MASTER_PRODUCT_DISABLED",
        message="상품을 사용중지했습니다.",
        data=master_service.set_product_active(db, auth, product_id, False),
    )


@router.post("/products/{product_id}/enable", response_model=ApiResult)
def enable_product_api(
    product_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_product_manage(auth)
    return api_success(
        result_code="MASTER_PRODUCT_ENABLED",
        message="상품을 재활성화했습니다.",
        data=master_service.set_product_active(db, auth, product_id, True),
    )


@router.post("/product-barcodes", response_model=ApiResult)
def create_product_barcode_api(
    request: ProductBarcodeCreateRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_product_manage(auth)
    return api_success(
        result_code="MASTER_PRODUCT_BARCODE_CREATED",
        message="상품바코드를 생성했습니다.",
        data=master_service.create_product_barcode(db, auth, request),
    )


@router.patch("/product-barcodes/{barcode_id}", response_model=ApiResult)
def update_product_barcode_api(
    barcode_id: int,
    request: ProductBarcodeUpdateRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_product_manage(auth)
    return api_success(
        result_code="MASTER_PRODUCT_BARCODE_UPDATED",
        message="상품바코드를 수정했습니다.",
        data=master_service.update_product_barcode(db, auth, barcode_id, request),
    )


@router.post("/product-barcodes/{barcode_id}/disable", response_model=ApiResult)
def disable_product_barcode_api(
    barcode_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_product_manage(auth)
    return api_success(
        result_code="MASTER_PRODUCT_BARCODE_DISABLED",
        message="상품바코드를 사용중지했습니다.",
        data=master_service.set_product_barcode_active(db, auth, barcode_id, False),
    )


@router.post("/product-barcodes/{barcode_id}/enable", response_model=ApiResult)
def enable_product_barcode_api(
    barcode_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_product_manage(auth)
    return api_success(
        result_code="MASTER_PRODUCT_BARCODE_ENABLED",
        message="상품바코드를 재활성화했습니다.",
        data=master_service.set_product_barcode_active(db, auth, barcode_id, True),
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


@router.post("/common-code-groups", response_model=ApiResult)
def create_common_code_group_api(
    request: CommonCodeGroupCreateRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_common_code_manage(auth)
    return api_success(
        result_code="MASTER_COMMON_CODE_GROUP_CREATED",
        message="怨듯넻肄붾뱶 洹몃９???앹꽦?덉뒿?덈떎.",
        data=master_service.create_common_code_group(db, auth, request),
    )


@router.patch("/common-code-groups/{group_id}", response_model=ApiResult)
def update_common_code_group_api(
    group_id: int,
    request: CommonCodeGroupUpdateRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_common_code_manage(auth)
    return api_success(
        result_code="MASTER_COMMON_CODE_GROUP_UPDATED",
        message="怨듯넻肄붾뱶 洹몃９???섏젙?덉뒿?덈떎.",
        data=master_service.update_common_code_group(db, auth, group_id, request),
    )


@router.post("/common-code-groups/{group_id}/disable", response_model=ApiResult)
def disable_common_code_group_api(
    group_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_common_code_manage(auth)
    return api_success(
        result_code="MASTER_COMMON_CODE_GROUP_DISABLED",
        message="怨듯넻肄붾뱶 洹몃９???ъ슜以묒??덉뒿?덈떎.",
        data=master_service.set_common_code_group_active(db, auth, group_id, False),
    )


@router.post("/common-code-groups/{group_id}/enable", response_model=ApiResult)
def enable_common_code_group_api(
    group_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_common_code_manage(auth)
    return api_success(
        result_code="MASTER_COMMON_CODE_GROUP_ENABLED",
        message="怨듯넻肄붾뱶 洹몃９???ы솢?깊솕?덉뒿?덈떎.",
        data=master_service.set_common_code_group_active(db, auth, group_id, True),
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


@router.post("/common-codes", response_model=ApiResult)
def create_common_code_api(
    request: CommonCodeCreateRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_common_code_manage(auth)
    return api_success(
        result_code="MASTER_COMMON_CODE_CREATED",
        message="怨듯넻肄붾뱶瑜??앹꽦?덉뒿?덈떎.",
        data=master_service.create_common_code(db, auth, request),
    )


@router.patch("/common-codes/{code_id}", response_model=ApiResult)
def update_common_code_api(
    code_id: int,
    request: CommonCodeUpdateRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_common_code_manage(auth)
    return api_success(
        result_code="MASTER_COMMON_CODE_UPDATED",
        message="怨듯넻肄붾뱶瑜??섏젙?덉뒿?덈떎.",
        data=master_service.update_common_code(db, auth, code_id, request),
    )


@router.post("/common-codes/{code_id}/disable", response_model=ApiResult)
def disable_common_code_api(
    code_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_common_code_manage(auth)
    return api_success(
        result_code="MASTER_COMMON_CODE_DISABLED",
        message="怨듯넻肄붾뱶瑜??ъ슜以묒??덉뒿?덈떎.",
        data=master_service.set_common_code_active(db, auth, code_id, False),
    )


@router.post("/common-codes/{code_id}/enable", response_model=ApiResult)
def enable_common_code_api(
    code_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_common_code_manage(auth)
    return api_success(
        result_code="MASTER_COMMON_CODE_ENABLED",
        message="怨듯넻肄붾뱶瑜??ы솢?깊솕?덉뒿?덈떎.",
        data=master_service.set_common_code_active(db, auth, code_id, True),
    )
