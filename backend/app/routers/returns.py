from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_auth_context, get_db
from app.core.permissions import require_password_change_completed
from app.schemas.auth import AuthContext
from app.schemas.common import ApiResult, api_success
from app.schemas.returns import ReturnIntakeBatchCreateRequest, ReturnIntakePasteRowsRequest
from app.services import return_intake_service


router = APIRouter(prefix="/api/returns", tags=["returns"])


def _ensure_password_ready(auth: AuthContext) -> None:
    require_password_change_completed(auth)


@router.post("/intake/batches", response_model=ApiResult)
def create_return_intake_batch_api(
    request: ReturnIntakeBatchCreateRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _ensure_password_ready(auth)
    return api_success(
        result_code="RETURN_INTAKE_BATCH_CREATED",
        message="반품 접수 batch를 생성했습니다.",
        data=return_intake_service.create_return_intake_batch(db, auth, request),
    )


@router.get("/intake/batches", response_model=ApiResult)
def list_return_intake_batches_api(
    client_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _ensure_password_ready(auth)
    return api_success(
        result_code="RETURN_INTAKE_BATCHES_FOUND",
        message="반품 접수 batch 목록을 조회했습니다.",
        data=return_intake_service.list_return_intake_batches(
            db,
            auth,
            client_id=client_id,
            page=page,
            page_size=page_size,
        ),
    )


@router.get("/intake/batches/{batch_id}", response_model=ApiResult)
def get_return_intake_batch_api(
    batch_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _ensure_password_ready(auth)
    return api_success(
        result_code="RETURN_INTAKE_BATCH_FOUND",
        message="반품 접수 batch 상세를 조회했습니다.",
        data=return_intake_service.get_return_intake_batch(db, auth, batch_id),
    )


@router.post("/intake/batches/{batch_id}/rows/paste", response_model=ApiResult)
def paste_return_intake_rows_api(
    batch_id: int,
    request: ReturnIntakePasteRowsRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _ensure_password_ready(auth)
    return api_success(
        result_code="RETURN_INTAKE_ROWS_SAVED",
        message="반품 접수 row를 저장했습니다.",
        data=return_intake_service.paste_return_intake_rows(db, auth, batch_id, request),
    )


@router.get("/intake/batches/{batch_id}/rows", response_model=ApiResult)
def list_return_intake_rows_api(
    batch_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _ensure_password_ready(auth)
    return api_success(
        result_code="RETURN_INTAKE_ROWS_FOUND",
        message="반품 접수 row 목록을 조회했습니다.",
        data=return_intake_service.list_return_intake_rows(db, auth, batch_id, page=page, page_size=page_size),
    )


@router.post("/intake/batches/{batch_id}/validate", response_model=ApiResult)
def validate_return_intake_batch_api(
    batch_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _ensure_password_ready(auth)
    return api_success(
        result_code="RETURN_INTAKE_VALIDATED",
        message="반품 접수 자료를 검증했습니다.",
        data=return_intake_service.validate_return_intake_batch(db, auth, batch_id),
    )


@router.post("/intake/batches/{batch_id}/prepare-processing", response_model=ApiResult)
def prepare_return_intake_batch_for_processing_api(
    batch_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _ensure_password_ready(auth)
    return api_success(
        result_code="RETURN_INTAKE_PREPARED_FOR_PROCESSING",
        message="반품처리 대기 대상을 생성했습니다.",
        data=return_intake_service.prepare_return_intake_batch_for_processing(db, auth, batch_id),
    )


@router.get("/processing/tasks", response_model=ApiResult)
def list_return_processing_tasks_api(
    client_id: int | None = None,
    batch_id: int | None = None,
    tracking_no: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _ensure_password_ready(auth)
    return api_success(
        result_code="RETURN_PROCESSING_TASKS_FOUND",
        message="반품처리 대기 대상 목록을 조회했습니다.",
        data=return_intake_service.list_return_processing_tasks(
            db,
            auth,
            client_id=client_id,
            batch_id=batch_id,
            tracking_no=tracking_no,
            status=status,
            page=page,
            page_size=page_size,
        ),
    )
