"""Import job read-only service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.auth_context import resolve_effective_client_id
from app.core.exceptions import AuthError, ClientScopeDeniedError
from app.core.permissions import require_permission
from app.repositories import import_repository as repo
from app.schemas.auth import AuthContext
from app.schemas.imports import (
    ImportJobDetailResponse,
    ImportJobErrorsResponse,
    ImportJobFileResponse,
    ImportJobListResponse,
    ImportJobRowResponse,
    ImportJobRowsResponse,
    ImportJobSummaryResponse,
    ImportValidationErrorResponse,
)


def _business_error(result_code: str, message: str, status_code: int = 400) -> AuthError:
    return AuthError(message, result_code=result_code, status_code=status_code)


def _safe_page(page: int) -> int:
    return max(page, 1)


def _safe_page_size(page_size: int) -> int:
    return min(max(page_size, 1), 200)


def _require_import_view(auth: AuthContext) -> None:
    require_permission(auth, "IMPORT_VIEW")


def _job_summary(job, client, warehouse) -> ImportJobSummaryResponse:
    return ImportJobSummaryResponse(
        job_id=job.id,
        import_type=job.import_type,
        source_type=job.source_type,
        source_name=job.source_name,
        requested_client_id=job.requested_client_id,
        requested_client_name=client.client_name if client else None,
        requested_warehouse_id=job.requested_warehouse_id,
        requested_warehouse_name=warehouse.warehouse_name if warehouse else None,
        status=job.status,
        total_rows=job.total_rows,
        valid_rows=job.valid_rows,
        invalid_rows=job.invalid_rows,
        error_rows=job.error_rows,
        progress_percent=job.progress_percent,
        file_name=job.file_name,
        worksheet_name=job.worksheet_name,
        created_by=job.created_by,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        updated_at=job.updated_at,
    )


def _job_detail(job, client, warehouse, files) -> ImportJobDetailResponse:
    return ImportJobDetailResponse(
        **_job_summary(job, client, warehouse).model_dump(),
        parsed_rows=job.parsed_rows,
        inserted_rows=job.inserted_rows,
        updated_rows=job.updated_rows,
        skipped_rows=job.skipped_rows,
        message=job.message,
        raw_json=job.raw_json,
        files=[
            ImportJobFileResponse(
                file_id=file.id,
                file_name=file.file_name,
                stored_file_name=file.stored_file_name,
                relative_path=file.relative_path,
                mime_type=file.mime_type,
                size_bytes=file.size_bytes,
                uploaded_by=file.uploaded_by,
                uploaded_at=file.uploaded_at,
            )
            for file in files
        ],
    )


def _row_response(row) -> ImportJobRowResponse:
    return ImportJobRowResponse(
        row_id=row.id,
        job_id=row.job_id,
        client_id=row.client_id,
        row_no=row.row_no,
        source_row_key=row.source_row_key,
        row_hash=row.row_hash,
        raw_json=row.raw_json,
        normalized_json=row.normalized_json,
        validation_status=row.validation_status,
        validation_message=row.validation_message,
        target_action=row.target_action,
        target_table=row.target_table,
        target_id=row.target_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _error_response(error) -> ImportValidationErrorResponse:
    return ImportValidationErrorResponse(
        error_id=error.id,
        job_id=error.job_id,
        row_id=error.row_id,
        row_no=error.row_no,
        field_name=error.field_name,
        raw_value=error.raw_value,
        error_code=error.error_code,
        error_message=error.error_message,
        severity=error.severity,
        created_at=error.created_at,
    )


def _ensure_job_access(auth: AuthContext, job) -> None:
    if job.requested_client_id is None:
        if auth.is_internal_user:
            return
        raise ClientScopeDeniedError("고객사 범위가 지정되지 않은 import job은 내부 운영자만 조회할 수 있습니다.")
    resolve_effective_client_id(auth, job.requested_client_id)


def list_import_jobs(
    db: Session,
    auth: AuthContext,
    *,
    client_id: int | None = None,
    import_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    _require_import_view(auth)
    effective_client_id = resolve_effective_client_id(auth, client_id, allow_all_clients=True)
    safe_page = _safe_page(page)
    safe_page_size = _safe_page_size(page_size)
    items = repo.list_import_jobs(
        db,
        client_id=effective_client_id,
        import_type=import_type,
        status=status,
        page=safe_page,
        page_size=safe_page_size,
    )
    total_count = repo.count_import_jobs(
        db,
        client_id=effective_client_id,
        import_type=import_type,
        status=status,
    )
    return ImportJobListResponse(
        items=[_job_summary(job, client_row, warehouse).model_dump() for job, client_row, warehouse in items],
        page=safe_page,
        page_size=safe_page_size,
        total_count=total_count,
    ).model_dump()


def get_import_job_detail(db: Session, auth: AuthContext, job_id: int) -> dict:
    _require_import_view(auth)
    row = repo.get_import_job(db, job_id)
    if row is None:
        raise _business_error("IMPORT_JOB_NOT_FOUND", "Import job을 찾을 수 없습니다.", 404)
    job, client_row, warehouse = row
    _ensure_job_access(auth, job)
    files = repo.list_import_job_files(db, job_id=job.id)
    return _job_detail(job, client_row, warehouse, files).model_dump()


def list_import_job_rows(
    db: Session,
    auth: AuthContext,
    *,
    job_id: int,
    validation_status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    _require_import_view(auth)
    row = repo.get_import_job(db, job_id)
    if row is None:
        raise _business_error("IMPORT_JOB_NOT_FOUND", "Import job을 찾을 수 없습니다.", 404)
    job, _, _ = row
    _ensure_job_access(auth, job)
    safe_page = _safe_page(page)
    safe_page_size = _safe_page_size(page_size)
    items = repo.list_import_job_rows(
        db,
        job_id=job_id,
        validation_status=validation_status,
        page=safe_page,
        page_size=safe_page_size,
    )
    total_count = repo.count_import_job_rows(
        db,
        job_id=job_id,
        validation_status=validation_status,
    )
    return ImportJobRowsResponse(
        items=[_row_response(item).model_dump() for item in items],
        page=safe_page,
        page_size=safe_page_size,
        total_count=total_count,
    ).model_dump()


def list_import_job_errors(
    db: Session,
    auth: AuthContext,
    *,
    job_id: int,
    severity: str | None = None,
    row_no: int | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    _require_import_view(auth)
    row = repo.get_import_job(db, job_id)
    if row is None:
        raise _business_error("IMPORT_JOB_NOT_FOUND", "Import job을 찾을 수 없습니다.", 404)
    job, _, _ = row
    _ensure_job_access(auth, job)
    safe_page = _safe_page(page)
    safe_page_size = _safe_page_size(page_size)
    items = repo.list_import_validation_errors(
        db,
        job_id=job_id,
        severity=severity,
        row_no=row_no,
        page=safe_page,
        page_size=safe_page_size,
    )
    total_count = repo.count_import_validation_errors(
        db,
        job_id=job_id,
        severity=severity,
        row_no=row_no,
    )
    return ImportJobErrorsResponse(
        items=[_error_response(item).model_dump() for item in items],
        page=safe_page,
        page_size=safe_page_size,
        total_count=total_count,
    ).model_dump()
