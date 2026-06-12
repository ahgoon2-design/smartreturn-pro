"""Import job API skeleton."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_auth_context, get_db
from app.core.permissions import require_password_change_completed
from app.schemas.auth import AuthContext
from app.schemas.common import ApiResult, api_success
from app.schemas.imports import (
    ImportAutoMapRequest,
    ImportJobCreateRequest,
    ImportMappingApplyRequest,
    ImportMappingProfileCreateRequest,
    ImportPasteRowsRequest,
    ImportValidationRunRequest,
)
from app.services import import_service


router = APIRouter(prefix="/api/import-jobs", tags=["imports"])


def _require_import_view(auth: AuthContext) -> None:
    require_password_change_completed(auth)


def _require_import_manage(auth: AuthContext) -> None:
    require_password_change_completed(auth)


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


@router.post("/{job_id}/files/excel", response_model=ApiResult)
async def upload_excel_import_job_file_api(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_import_manage(auth)
    file_name, mime_type, file_bytes = import_service.extract_multipart_file(
        await request.body(),
        request.headers.get("content-type", ""),
    )
    return api_success(
        result_code="IMPORT_JOB_EXCEL_FILE_UPLOADED",
        message="Excel file import rows saved.",
        data=import_service.upload_excel_import_job_file(
            db,
            auth,
            job_id=job_id,
            file_name=file_name,
            mime_type=mime_type,
            file_bytes=file_bytes,
        ),
    )


@router.get("/source-types", response_model=ApiResult)
def list_import_source_types_api(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_import_view(auth)
    return api_success(
        result_code="IMPORT_SOURCE_TYPES_FOUND",
        message="Import source type 목록을 조회했습니다.",
        data=import_service.list_import_source_types(db, auth),
    )


@router.get("/source-types/{import_type}/fields", response_model=ApiResult)
def get_import_source_type_fields_api(
    import_type: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_import_view(auth)
    return api_success(
        result_code="IMPORT_SOURCE_TYPE_FIELDS_FOUND",
        message="Import field 목록을 조회했습니다.",
        data=import_service.get_import_source_type_fields(db, auth, import_type),
    )


@router.get("/mapping-profiles", response_model=ApiResult)
def list_import_mapping_profiles_api(
    client_id: int | None = None,
    import_type: str | None = None,
    source_type: str | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_import_view(auth)
    return api_success(
        result_code="IMPORT_MAPPING_PROFILES_FOUND",
        message="Import mapping profile 목록을 조회했습니다.",
        data=import_service.list_mapping_profiles(
            db,
            auth,
            client_id=client_id,
            import_type=import_type,
            source_type=source_type,
        ),
    )


@router.post("/mapping-profiles", response_model=ApiResult)
def create_import_mapping_profile_api(
    request: ImportMappingProfileCreateRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_import_manage(auth)
    return api_success(
        result_code="IMPORT_MAPPING_PROFILE_SAVED",
        message="Import mapping profile을 저장했습니다.",
        data=import_service.create_mapping_profile(db, auth, request),
    )


@router.get("/templates/{import_type}")
def download_import_template_api(
    import_type: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> Response:
    _require_import_view(auth)
    file_name, content = import_service.build_import_template(db, auth, import_type)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.post("/{job_id}/auto-map", response_model=ApiResult)
def auto_map_import_job_api(
    job_id: int,
    request: ImportAutoMapRequest | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_import_manage(auth)
    return api_success(
        result_code="IMPORT_JOB_AUTO_MAPPED",
        message="Import job 컬럼 매핑 추천을 적용했습니다.",
        data=import_service.auto_map_import_job(
            db,
            auth,
            job_id=job_id,
            request=request or ImportAutoMapRequest(),
        ),
    )


@router.put("/{job_id}/mapping", response_model=ApiResult)
def apply_import_job_mapping_api(
    job_id: int,
    request: ImportMappingApplyRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_import_manage(auth)
    return api_success(
        result_code="IMPORT_JOB_MAPPING_APPLIED",
        message="Import job 컬럼 매핑을 적용했습니다.",
        data=import_service.apply_import_job_mapping(db, auth, job_id=job_id, request=request),
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


@router.post("/{job_id}/confirm", response_model=ApiResult)
def confirm_import_job_api(
    job_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_import_manage(auth)
    data = import_service.confirm_import_job(db, auth, job_id=job_id)
    return api_success(
        result_code=data["result_code"],
        message=data["message"],
        data=data,
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
