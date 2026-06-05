from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_auth_context, get_db
from app.core.permissions import require_password_change_completed
from app.schemas.auth import AuthContext
from app.schemas.common import ApiResult, api_success
from app.schemas.returns import (
    ReturnClosingConfirmRequest,
    ReturnDisposalConfirmRequest,
    ReturnExternalOutboundConfirmRequest,
    ReturnHoldRejudgeRequest,
    ReturnHoldUpdateRequest,
    ReturnIntakeBatchCreateRequest,
    ReturnIntakePasteRowsRequest,
    ReturnProcessingJudgeRequest,
)
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


@router.post("/processing/tasks/{task_id}/judge", response_model=ApiResult)
def judge_return_processing_task_api(
    task_id: int,
    request: ReturnProcessingJudgeRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _ensure_password_ready(auth)
    return api_success(
        result_code="RETURN_PROCESSING_TASK_JUDGED",
        message="반품처리 판정을 저장했습니다.",
        data=return_intake_service.judge_return_processing_task(db, auth, task_id, request),
    )


@router.post("/processing/tasks/{task_id}/attachments", response_model=ApiResult)
async def upload_return_processing_attachment_api(
    task_id: int,
    file: UploadFile = File(...),
    attachment_type: str | None = Form(None),
    note: str | None = Form(None),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _ensure_password_ready(auth)
    file_bytes = await file.read()
    return api_success(
        result_code="RETURN_PROCESSING_ATTACHMENT_UPLOADED",
        message="반품처리 증빙 파일을 업로드했습니다.",
        data=return_intake_service.upload_return_processing_attachment(
            db,
            auth,
            task_id,
            filename=file.filename or "",
            content_type=file.content_type,
            file_bytes=file_bytes,
            attachment_type=attachment_type,
            note=note,
        ),
    )


@router.get("/processing/tasks/{task_id}/attachments", response_model=ApiResult)
def list_return_processing_attachments_api(
    task_id: int,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _ensure_password_ready(auth)
    return api_success(
        result_code="RETURN_PROCESSING_ATTACHMENTS_FOUND",
        message="반품처리 증빙 파일 목록을 조회했습니다.",
        data=return_intake_service.list_return_processing_attachments(
            db,
            auth,
            task_id,
            include_inactive=include_inactive,
        ),
    )


@router.post("/processing/tasks/{task_id}/attachments/{attachment_id}/disable", response_model=ApiResult)
def disable_return_processing_attachment_api(
    task_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _ensure_password_ready(auth)
    return api_success(
        result_code="RETURN_PROCESSING_ATTACHMENT_DISABLED",
        message="반품처리 증빙 파일을 비활성화했습니다.",
        data=return_intake_service.disable_return_processing_attachment(db, auth, task_id, attachment_id),
    )


@router.get("/closing/candidates", response_model=ApiResult)
def list_return_closing_candidates_api(
    client_id: int | None = None,
    judgement_status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _ensure_password_ready(auth)
    return api_success(
        result_code="RETURN_CLOSING_CANDIDATES_FOUND",
        message="반품 일마감 후보를 조회했습니다.",
        data=return_intake_service.list_return_closing_candidates(
            db,
            auth,
            client_id=client_id,
            judgement_status=judgement_status,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        ),
    )


@router.post("/closing/confirm", response_model=ApiResult)
def confirm_return_closing_api(
    request: ReturnClosingConfirmRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _ensure_password_ready(auth)
    return api_success(
        result_code="RETURN_CLOSING_CONFIRMED",
        message="반품 일마감을 확정했습니다.",
        data=return_intake_service.confirm_return_closing(db, auth, request),
    )


@router.get("/external-outbound/candidates", response_model=ApiResult)
def list_return_external_outbound_candidates_api(
    client_id: int | None = None,
    judgement_status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    return_management_no: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _ensure_password_ready(auth)
    return api_success(
        result_code="RETURN_EXTERNAL_OUTBOUND_CANDIDATES_FOUND",
        message="반품 외부반출 후보를 조회했습니다.",
        data=return_intake_service.list_return_external_outbound_candidates(
            db,
            auth,
            client_id=client_id,
            judgement_status=judgement_status,
            date_from=date_from,
            date_to=date_to,
            return_management_no=return_management_no,
            page=page,
            page_size=page_size,
        ),
    )


@router.post("/external-outbound/confirm", response_model=ApiResult)
def confirm_return_external_outbound_api(
    request: ReturnExternalOutboundConfirmRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _ensure_password_ready(auth)
    return api_success(
        result_code="RETURN_EXTERNAL_OUTBOUND_CONFIRMED",
        message="반품 외부반출을 확정했습니다.",
        data=return_intake_service.confirm_return_external_outbound(db, auth, request),
    )


@router.get("/hold/candidates", response_model=ApiResult)
def list_return_hold_candidates_api(
    client_id: int | None = None,
    hold_status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    return_management_no: str | None = None,
    tracking_no: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _ensure_password_ready(auth)
    return api_success(
        result_code="RETURN_HOLD_CANDIDATES_FOUND",
        message="반품 보류 후보를 조회했습니다.",
        data=return_intake_service.list_return_hold_candidates(
            db,
            auth,
            client_id=client_id,
            hold_status=hold_status,
            date_from=date_from,
            date_to=date_to,
            return_management_no=return_management_no,
            tracking_no=tracking_no,
            page=page,
            page_size=page_size,
        ),
    )


@router.patch("/hold/tasks/{task_id}", response_model=ApiResult)
def update_return_hold_task_api(
    task_id: int,
    request: ReturnHoldUpdateRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _ensure_password_ready(auth)
    return api_success(
        result_code="RETURN_HOLD_UPDATED",
        message="반품 보류 정보를 저장했습니다.",
        data=return_intake_service.update_return_hold_task(db, auth, task_id, request),
    )


@router.post("/hold/tasks/{task_id}/rejudge", response_model=ApiResult)
def rejudge_return_hold_task_api(
    task_id: int,
    request: ReturnHoldRejudgeRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _ensure_password_ready(auth)
    return api_success(
        result_code="RETURN_HOLD_REJUDGED",
        message="반품 보류 대상을 재판정했습니다.",
        data=return_intake_service.rejudge_return_hold_task(db, auth, task_id, request),
    )


@router.get("/disposal/candidates", response_model=ApiResult)
def list_return_disposal_candidates_api(
    client_id: int | None = None,
    disposal_status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    return_management_no: str | None = None,
    tracking_no: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _ensure_password_ready(auth)
    return api_success(
        result_code="RETURN_DISPOSAL_CANDIDATES_FOUND",
        message="반품 폐기 후보를 조회했습니다.",
        data=return_intake_service.list_return_disposal_candidates(
            db,
            auth,
            client_id=client_id,
            disposal_status=disposal_status,
            date_from=date_from,
            date_to=date_to,
            return_management_no=return_management_no,
            tracking_no=tracking_no,
            page=page,
            page_size=page_size,
        ),
    )


@router.post("/disposal/tasks/{task_id}/confirm", response_model=ApiResult)
def confirm_return_disposal_task_api(
    task_id: int,
    request: ReturnDisposalConfirmRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _ensure_password_ready(auth)
    return api_success(
        result_code="RETURN_DISPOSAL_CONFIRMED",
        message="반품 폐기를 확정했습니다.",
        data=return_intake_service.confirm_return_disposal_task(db, auth, task_id, request),
    )
