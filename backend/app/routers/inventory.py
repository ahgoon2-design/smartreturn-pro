from __future__ import annotations

from datetime import datetime

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


@router.get("/events", response_model=ApiResult)
def list_inventory_events_api(
    client_id: int | None = None,
    warehouse_id: int | None = None,
    product_code: str | None = None,
    barcode: str | None = None,
    keyword: str | None = None,
    event_type: str | None = None,
    source_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    require_password_change_completed(auth)
    return api_success(
        result_code="INVENTORY_EVENTS_FOUND",
        message="재고 이벤트 이력을 조회했습니다.",
        data=inventory_service.list_inventory_events(
            db,
            auth,
            client_id=client_id,
            warehouse_id=warehouse_id,
            product_code=product_code,
            barcode=barcode,
            keyword=keyword,
            event_type=event_type,
            source_type=source_type,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        ),
    )
