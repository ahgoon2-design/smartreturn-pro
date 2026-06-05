from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_auth_context, get_db
from app.core.permissions import require_password_change_completed
from app.schemas.auth import AuthContext
from app.schemas.common import ApiResult, api_success
from app.services import inventory_service


router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("/current", response_model=ApiResult)
def list_current_inventory_api(
    client_id: int | None = None,
    warehouse_id: int | None = None,
    product_code: str | None = None,
    barcode: str | None = None,
    keyword: str | None = None,
    stock_status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    require_password_change_completed(auth)
    return api_success(
        result_code="INVENTORY_CURRENT_FOUND",
        message="재고현황을 조회했습니다.",
        data=inventory_service.list_current_inventory(
            db,
            auth,
            client_id=client_id,
            warehouse_id=warehouse_id,
            product_code=product_code,
            barcode=barcode,
            keyword=keyword,
            stock_status=stock_status,
            page=page,
            page_size=page_size,
        ),
    )
