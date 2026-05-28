"""Import job API skeleton."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_auth_context, get_db
from app.core.permissions import require_password_change_completed, require_permission, require_roles
from app.schemas.auth import AuthContext
from app.schemas.common import ApiResult, api_success
from app.schemas.imports import ImportJobCreateRequest, ImportPasteRowsRequest, ImportValidationRunRequest
from app.services import import_service


router = APIRouter(prefix="/api/import-jobs", tags=["imports"])


def _require_import_view(auth: AuthContext) -> None:
    require_password_change_completed(auth)


def _require_import_manage(auth: AuthContext) -> None:
    require_password_change_completed(auth)
    require_roles(auth, {"SUPER_ADMIN", "INTERNAL_ADMIN"})
    require_permission(auth, "IMPORT_MANAGE")


@router.post("", response_model=ApiResult)
def create_import_job_api(
    request: ImportJobCreateRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_import_manage(auth)
    return api_success(
        result_code="IMPORT_JOB_CREATED",
        message="Import job이 생성되었습니다.",
        data=import_service.create_import_job(db, auth, request),
    )


@router.post("/{job_id}/rows/paste", response_model=ApiResult)
def save_paste_import_job_rows_api(
    job_id: int,
    request: ImportPasteRowsRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_import_manage(auth)
    return api_success(
        result_code="IMPORT_JOB_ROWS_SAVED",
        message="Import job row瑜???덉뒿?덈떎.",
        data=import_service.save_paste_import_job_rows(db, auth, job_id=job_id, request=request),
    )


@router.post("/{job_id}/validate", response_model=ApiResult)
def validate_import_job_api(
    job_id: int,
    request: ImportValidationRunRequest | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_import_manage(auth)
    return api_success(
        result_code="IMPORT_JOB_VALIDATED",
        message="Import job validation completed.",
        data=import_service.validate_import_job(
            db,
            auth,
            job_id=job_id,
            request=request or ImportValidationRunRequest(),
        ),
    )


@router.get("", response_model=ApiResult)
def list_import_jobs_api(
    client_id: int | None = None,
    import_type: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_import_view(auth)
    return api_success(
        result_code="IMPORT_JOB_LIST_FOUND",
        message="Import job 목록을 조회했습니다.",
        data=import_service.list_import_jobs(
            db,
            auth,
            client_id=client_id,
            import_type=import_type,
            status=status,
            page=page,
            page_size=page_size,
        ),
    )


@router.get("/{job_id}", response_model=ApiResult)
def get_import_job_api(
    job_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_import_view(auth)
    return api_success(
        result_code="IMPORT_JOB_FOUND",
        message="Import job 상세를 조회했습니다.",
        data=import_service.get_import_job_detail(db, auth, job_id),
    )


@router.get("/{job_id}/rows", response_model=ApiResult)
def list_import_job_rows_api(
    job_id: int,
    validation_status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_import_view(auth)
    return api_success(
        result_code="IMPORT_JOB_ROWS_FOUND",
        message="Import job 행 목록을 조회했습니다.",
        data=import_service.list_import_job_rows(
            db,
            auth,
            job_id=job_id,
            validation_status=validation_status,
            page=page,
            page_size=page_size,
        ),
    )


@router.get("/{job_id}/errors", response_model=ApiResult)
def list_import_job_errors_api(
    job_id: int,
    severity: str | None = None,
    row_no: int | None = Query(None, ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_import_view(auth)
    return api_success(
        result_code="IMPORT_JOB_ERRORS_FOUND",
        message="Import job 검증 오류를 조회했습니다.",
        data=import_service.list_import_job_errors(
            db,
            auth,
            job_id=job_id,
            severity=severity,
            row_no=row_no,
            page=page,
            page_size=page_size,
        ),
    )
