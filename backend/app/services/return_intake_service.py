from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.auth_context import resolve_effective_client_id
from app.core.exceptions import AuthError, ClientScopeDeniedError, PermissionDeniedError
from app.core.permissions import can_write, require_permission, require_roles
from app.models.inventory import InventoryEvent
from app.models.returns import ReturnIntakeRow, ReturnProcessingAttachment
from app.repositories import inventory_repository
from app.repositories import master_repository
from app.repositories import return_intake_repository as repo
from app.schemas.auth import AuthContext
from app.schemas.returns import (
    ReturnIntakeBatchCreateRequest,
    ReturnIntakeBatchDetailResponse,
    ReturnIntakeBatchListResponse,
    ReturnIntakeBatchSummaryResponse,
    ReturnIntakePasteRowsRequest,
    ReturnIntakePasteRowsResponse,
    ReturnIntakePrepareProcessingResponse,
    ReturnIntakeRowResponse,
    ReturnIntakeRowsResponse,
    ReturnProcessingAttachmentListResponse,
    ReturnProcessingAttachmentResponse,
    ReturnClosingCandidateListResponse,
    ReturnClosingCandidateResponse,
    ReturnClosingConfirmRequest,
    ReturnClosingConfirmResponse,
    ReturnClosingRowResult,
    ReturnExternalOutboundCandidateListResponse,
    ReturnExternalOutboundCandidateResponse,
    ReturnExternalOutboundConfirmRequest,
    ReturnExternalOutboundConfirmResponse,
    ReturnExternalOutboundRowResult,
    ReturnDisposalCandidateListResponse,
    ReturnDisposalCandidateResponse,
    ReturnDisposalConfirmRequest,
    ReturnDisposalConfirmResponse,
    ReturnHoldCandidateListResponse,
    ReturnHoldCandidateResponse,
    ReturnHoldRejudgeRequest,
    ReturnHoldRejudgeResponse,
    ReturnHoldUpdateRequest,
    ReturnHoldUpdateResponse,
    ReturnProcessingJudgeRequest,
    ReturnProcessingJudgeResponse,
    ReturnProcessingTaskListResponse,
    ReturnProcessingTaskResponse,
    ReturnIntakeValidateResponse,
)


BATCH_STATUS_DRAFT = "DRAFT"
BATCH_STATUS_RECEIVED = "RECEIVED"
BATCH_STATUS_VALIDATED = "VALIDATED"
BATCH_STATUS_HAS_ERRORS = "HAS_ERRORS"
BATCH_STATUS_READY_FOR_PROCESSING = "READY_FOR_PROCESSING"

ROW_VALIDATION_NOT_VALIDATED = "NOT_VALIDATED"
ROW_VALIDATION_VALID = "VALID"
ROW_VALIDATION_WARNING = "WARNING"
ROW_VALIDATION_INVALID = "INVALID"

ROW_STATUS_RECEIVED = "RECEIVED"
ROW_STATUS_READY_FOR_PROCESSING = "READY_FOR_PROCESSING"
ROW_STATUS_PROCESSING = "PROCESSING"
ROW_STATUS_COMPLETED = "COMPLETED"
ROW_STATUS_HOLD = "HOLD"

JUDGEMENT_GOOD = "GOOD"
JUDGEMENT_REFURB = "REFURB"
JUDGEMENT_SAMPLE = "SAMPLE"
JUDGEMENT_MANUFACTURER_RETURN = "MANUFACTURER_RETURN"
JUDGEMENT_DISPOSAL = "DISPOSAL"
JUDGEMENT_HOLD = "HOLD"

ALLOWED_JUDGEMENT_STATUSES = {
    JUDGEMENT_GOOD,
    JUDGEMENT_REFURB,
    JUDGEMENT_SAMPLE,
    JUDGEMENT_MANUFACTURER_RETURN,
    JUDGEMENT_DISPOSAL,
    JUDGEMENT_HOLD,
}
LABEL_REQUIRED_JUDGEMENT_STATUSES = {
    JUDGEMENT_REFURB,
    JUDGEMENT_SAMPLE,
    JUDGEMENT_MANUFACTURER_RETURN,
    JUDGEMENT_HOLD,
}
LABEL_STATUS_NOT_REQUIRED = "NOT_REQUIRED"
LABEL_STATUS_LOCAL_AGENT_NOT_CONNECTED = "LOCAL_AGENT_NOT_CONNECTED"

RETURN_CLOSING_EVENT_TYPE_GOOD_IN = "RETURN_GOOD_IN"
RETURN_CLOSING_SOURCE_TYPE = "RETURN_CLOSING"
RETURN_CLOSING_STOCK_STATUS_GOOD = "GOOD"
RETURN_GOOD_WAREHOUSE_USAGE_PRIORITY = ("RETURN_GOOD", "INBOUND")
RETURN_CLOSING_ACTION_INVENTORY_TARGET = "INVENTORY_REFLECT_TARGET"
RETURN_CLOSING_ACTION_FOLLOWUP_TARGET = "FOLLOWUP_TARGET"

EXTERNAL_OUTBOUND_JUDGEMENT_STATUSES = {
    JUDGEMENT_REFURB,
    JUDGEMENT_SAMPLE,
    JUDGEMENT_MANUFACTURER_RETURN,
}
EXTERNAL_OUTBOUND_STATUS_NOT_REQUIRED = "NOT_REQUIRED"
EXTERNAL_OUTBOUND_STATUS_READY = "READY"
EXTERNAL_OUTBOUND_STATUS_CONFIRMED = "CONFIRMED"

HOLD_STATUS_PENDING = "HOLD_PENDING"
HOLD_STATUS_CUSTOMER_CHECKING = "CUSTOMER_CHECKING"
HOLD_STATUS_READY_TO_REJUDGE = "READY_TO_REJUDGE"
HOLD_STATUS_RESOLVED = "RESOLVED"
ALLOWED_HOLD_STATUSES = {
    HOLD_STATUS_PENDING,
    HOLD_STATUS_CUSTOMER_CHECKING,
    HOLD_STATUS_READY_TO_REJUDGE,
    HOLD_STATUS_RESOLVED,
}

DISPOSAL_STATUS_PENDING = "DISPOSAL_PENDING"
DISPOSAL_STATUS_CONFIRMED = "DISPOSAL_CONFIRMED"

ATTACHMENT_TYPE_PHOTO = "PHOTO"
ALLOWED_ATTACHMENT_TYPES = {ATTACHMENT_TYPE_PHOTO, "EVIDENCE"}
ALLOWED_ATTACHMENT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_ATTACHMENT_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
RETURN_PROCESSING_UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads" / "return-processing"

ALLOWED_SOURCE_TYPES = {"PASTE", "MANUAL"}


def _business_error(result_code: str, message: str, status_code: int = 400) -> AuthError:
    return AuthError(message, result_code=result_code, status_code=status_code)


def _require_return_view(auth: AuthContext) -> None:
    require_permission(auth, "RETURN_VIEW")


def _require_return_prepare(auth: AuthContext) -> None:
    if not can_write(auth):
        raise PermissionDeniedError("읽기 전용 사용자는 반품 접수 자료를 변경할 수 없습니다.")
    require_roles(auth, {"SUPER_ADMIN", "INTERNAL_ADMIN", "INTERNAL_WORKER", "CLIENT_ADMIN", "CLIENT_USER"})
    require_permission(auth, "RETURN_PREPARE")


def _safe_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _safe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_barcode(value: str | None) -> str | None:
    text = _safe_text(value)
    if text is None:
        return None
    return "".join(text.split())


def _mask_phone(value: str | None) -> str | None:
    text = _safe_text(value)
    if text is None:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return "***"
    return f"****{digits[-4:]}"


def _ensure_source_type(source_type: str) -> str:
    normalized = source_type.strip().upper()
    if normalized not in ALLOWED_SOURCE_TYPES:
        raise _business_error("RETURN_INTAKE_SOURCE_TYPE_INVALID", "지원하지 않는 반품 접수 source_type입니다.")
    return normalized


def _ensure_client(db: Session, client_id: int):
    client = master_repository.get_client(db, client_id)
    if client is None:
        raise _business_error("RETURN_INTAKE_CLIENT_NOT_FOUND", "고객사를 찾을 수 없습니다.", 404)
    if not client.active_yn:
        raise _business_error("RETURN_INTAKE_CLIENT_INACTIVE", "사용중지 고객사에는 반품 접수 자료를 등록할 수 없습니다.")
    return client


def _get_batch_for_auth(db: Session, auth: AuthContext, batch_id: int):
    row = repo.get_batch_with_client(db, batch_id)
    if row is None:
        raise _business_error("RETURN_INTAKE_BATCH_NOT_FOUND", "반품 접수 batch를 찾을 수 없습니다.", 404)
    batch, _client = row
    resolve_effective_client_id(auth, batch.client_id)
    return row


def _batch_summary(batch, client) -> dict:
    return ReturnIntakeBatchSummaryResponse(
        batch_id=batch.id,
        client_id=batch.client_id,
        client_code=client.client_code,
        client_name=client.client_name,
        source_type=batch.source_type,
        source_name=batch.source_name,
        status=batch.status,
        total_rows=batch.total_rows,
        valid_rows=batch.valid_rows,
        warning_rows=batch.warning_rows,
        error_rows=batch.error_rows,
        memo=batch.memo,
        created_by=batch.created_by,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
    ).model_dump()


def _batch_detail(batch, client) -> dict:
    return ReturnIntakeBatchDetailResponse(**_batch_summary(batch, client)).model_dump()


def _row_response(row: ReturnIntakeRow) -> dict:
    return ReturnIntakeRowResponse(
        row_id=row.id,
        batch_id=row.batch_id,
        client_id=row.client_id,
        row_no=row.row_no,
        order_no=row.order_no,
        return_tracking_no=row.return_tracking_no,
        original_tracking_no=row.original_tracking_no,
        product_code=row.product_code,
        barcode=row.barcode,
        product_name=row.product_name,
        option_name=row.option_name,
        qty=row.qty,
        return_reason=row.return_reason,
        customer_name=row.customer_name,
        customer_phone_masked=row.customer_phone_masked,
        raw_data=row.raw_data,
        validation_status=row.validation_status,
        validation_message=row.validation_message,
        status=row.status,
        judgement_status=row.judgement_status,
        judgement_memo=row.judgement_memo,
        judged_at=row.judged_at,
        judged_by=row.judged_by,
        return_management_no=row.return_management_no,
        return_label_no=row.return_label_no,
        label_print_required=row.label_print_required,
        label_print_status=row.label_print_status,
        label_printed_at=row.label_printed_at,
        inventory_reflected_yn=row.inventory_reflected_yn,
        inventory_reflected_at=row.inventory_reflected_at,
        inventory_event_id=row.inventory_event_id,
        external_outbound_required=row.external_outbound_required,
        external_outbound_status=row.external_outbound_status,
        external_outbound_at=row.external_outbound_at,
        external_outbound_confirmed_by=row.external_outbound_confirmed_by,
        hold_status=row.hold_status,
        hold_reason=row.hold_reason,
        hold_response_memo=row.hold_response_memo,
        hold_resolved_at=row.hold_resolved_at,
        hold_resolved_by=row.hold_resolved_by,
        disposal_status=row.disposal_status,
        disposal_reason=row.disposal_reason,
        disposal_memo=row.disposal_memo,
        disposal_confirmed_at=row.disposal_confirmed_at,
        disposal_confirmed_by=row.disposal_confirmed_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    ).model_dump()


def _processing_task_response(row: ReturnIntakeRow, client) -> dict:
    return ReturnProcessingTaskResponse(
        task_id=row.id,
        row_id=row.id,
        batch_id=row.batch_id,
        client_id=row.client_id,
        client_code=client.client_code,
        client_name=client.client_name,
        row_no=row.row_no,
        order_no=row.order_no,
        return_tracking_no=row.return_tracking_no,
        original_tracking_no=row.original_tracking_no,
        product_code=row.product_code,
        barcode=row.barcode,
        product_name=row.product_name,
        option_name=row.option_name,
        qty=row.qty,
        return_reason=row.return_reason,
        validation_status=row.validation_status,
        status=row.status,
        judgement_status=row.judgement_status,
        judgement_memo=row.judgement_memo,
        judged_at=row.judged_at,
        judged_by=row.judged_by,
        return_management_no=row.return_management_no,
        return_label_no=row.return_label_no,
        label_print_required=row.label_print_required,
        label_print_status=row.label_print_status,
        label_printed_at=row.label_printed_at,
        inventory_reflected_yn=row.inventory_reflected_yn,
        inventory_reflected_at=row.inventory_reflected_at,
        inventory_event_id=row.inventory_event_id,
        external_outbound_required=row.external_outbound_required,
        external_outbound_status=row.external_outbound_status,
        external_outbound_at=row.external_outbound_at,
        external_outbound_confirmed_by=row.external_outbound_confirmed_by,
        hold_status=row.hold_status,
        hold_reason=row.hold_reason,
        hold_response_memo=row.hold_response_memo,
        hold_resolved_at=row.hold_resolved_at,
        hold_resolved_by=row.hold_resolved_by,
        disposal_status=row.disposal_status,
        disposal_reason=row.disposal_reason,
        disposal_memo=row.disposal_memo,
        disposal_confirmed_at=row.disposal_confirmed_at,
        disposal_confirmed_by=row.disposal_confirmed_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    ).model_dump()


def _closing_candidate_response(row: ReturnIntakeRow, client) -> dict:
    is_good = row.judgement_status == JUDGEMENT_GOOD
    return ReturnClosingCandidateResponse(
        row_id=row.id,
        task_id=row.id,
        batch_id=row.batch_id,
        client_id=row.client_id,
        client_code=client.client_code,
        client_name=client.client_name,
        row_no=row.row_no,
        order_no=row.order_no,
        return_tracking_no=row.return_tracking_no,
        product_code=row.product_code,
        barcode=row.barcode,
        product_name=row.product_name,
        qty=row.qty,
        judgement_status=row.judgement_status or "",
        return_management_no=row.return_management_no,
        return_label_no=row.return_label_no,
        status=row.status,
        inventory_reflected_yn=row.inventory_reflected_yn,
        inventory_reflected_at=row.inventory_reflected_at,
        inventory_event_id=row.inventory_event_id,
        judged_at=row.judged_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        closing_action=(
            RETURN_CLOSING_ACTION_INVENTORY_TARGET if is_good else RETURN_CLOSING_ACTION_FOLLOWUP_TARGET
        ),
        message=("GOOD/양품 정상재고 반영 대상입니다." if is_good else "정상재고 반영 없이 후속 처리 대상으로 남깁니다."),
    ).model_dump()


def _external_outbound_candidate_response(row: ReturnIntakeRow, client) -> dict:
    return ReturnExternalOutboundCandidateResponse(
        row_id=row.id,
        task_id=row.id,
        batch_id=row.batch_id,
        client_id=row.client_id,
        client_code=client.client_code,
        client_name=client.client_name,
        row_no=row.row_no,
        order_no=row.order_no,
        return_tracking_no=row.return_tracking_no,
        product_code=row.product_code,
        barcode=row.barcode,
        product_name=row.product_name,
        option_name=row.option_name,
        qty=row.qty,
        judgement_status=row.judgement_status or "",
        return_management_no=row.return_management_no,
        return_label_no=row.return_label_no,
        external_outbound_required=row.external_outbound_required,
        external_outbound_status=row.external_outbound_status,
        external_outbound_at=row.external_outbound_at,
        external_outbound_confirmed_by=row.external_outbound_confirmed_by,
        judged_at=row.judged_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    ).model_dump()


def _hold_candidate_response(row: ReturnIntakeRow, client) -> dict:
    return ReturnHoldCandidateResponse(
        row_id=row.id,
        task_id=row.id,
        batch_id=row.batch_id,
        client_id=row.client_id,
        client_code=client.client_code,
        client_name=client.client_name,
        row_no=row.row_no,
        order_no=row.order_no,
        return_tracking_no=row.return_tracking_no,
        product_code=row.product_code,
        barcode=row.barcode,
        product_name=row.product_name,
        option_name=row.option_name,
        qty=row.qty,
        return_reason=row.return_reason,
        judgement_status=row.judgement_status or "",
        judgement_memo=row.judgement_memo,
        hold_status=row.hold_status,
        hold_reason=row.hold_reason,
        hold_response_memo=row.hold_response_memo,
        hold_resolved_at=row.hold_resolved_at,
        hold_resolved_by=row.hold_resolved_by,
        return_management_no=row.return_management_no,
        return_label_no=row.return_label_no,
        judged_at=row.judged_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    ).model_dump()


def _disposal_candidate_response(row: ReturnIntakeRow, client) -> dict:
    return ReturnDisposalCandidateResponse(
        row_id=row.id,
        task_id=row.id,
        batch_id=row.batch_id,
        client_id=row.client_id,
        client_code=client.client_code,
        client_name=client.client_name,
        row_no=row.row_no,
        order_no=row.order_no,
        return_tracking_no=row.return_tracking_no,
        product_code=row.product_code,
        barcode=row.barcode,
        product_name=row.product_name,
        option_name=row.option_name,
        qty=row.qty,
        return_reason=row.return_reason,
        judgement_status=row.judgement_status or "",
        judgement_memo=row.judgement_memo,
        disposal_status=row.disposal_status,
        disposal_reason=row.disposal_reason,
        disposal_memo=row.disposal_memo,
        disposal_confirmed_at=row.disposal_confirmed_at,
        disposal_confirmed_by=row.disposal_confirmed_by,
        return_management_no=row.return_management_no,
        return_label_no=row.return_label_no,
        judged_at=row.judged_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    ).model_dump()


def _attachment_response(attachment: ReturnProcessingAttachment) -> dict:
    return ReturnProcessingAttachmentResponse(
        attachment_id=attachment.id,
        task_id=attachment.return_intake_row_id,
        row_id=attachment.return_intake_row_id,
        batch_id=attachment.batch_id,
        client_id=attachment.client_id,
        attachment_type=attachment.attachment_type,
        original_filename=attachment.original_filename,
        content_type=attachment.content_type,
        file_size=attachment.file_size,
        note=attachment.note,
        uploaded_by=attachment.uploaded_by,
        uploaded_at=attachment.uploaded_at,
        active_yn=attachment.active_yn,
        preview_url=None,
        download_url=None,
    ).model_dump()


def create_return_intake_batch(db: Session, auth: AuthContext, request: ReturnIntakeBatchCreateRequest) -> dict:
    _require_return_prepare(auth)
    client_id = resolve_effective_client_id(auth, request.client_id)
    if client_id is None:
        raise ClientScopeDeniedError("반품 접수 batch에는 client_id가 필요합니다.")
    source_type = _ensure_source_type(request.source_type)
    _ensure_client(db, client_id)

    try:
        batch = repo.create_batch(
            db,
            client_id=client_id,
            source_type=source_type,
            source_name=request.source_name,
            status=BATCH_STATUS_DRAFT,
            created_by=auth.user_id,
            memo=request.memo,
        )
        db.commit()
        batch_row = repo.get_batch_with_client(db, batch.id)
        if batch_row is None:
            raise _business_error("RETURN_INTAKE_BATCH_NOT_FOUND", "반품 접수 batch를 찾을 수 없습니다.", 404)
        return _batch_detail(*batch_row)
    except Exception:
        db.rollback()
        raise


def list_return_intake_batches(
    db: Session,
    auth: AuthContext,
    *,
    client_id: int | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    _require_return_view(auth)
    effective_client_id = resolve_effective_client_id(auth, client_id, allow_all_clients=True)
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 200)
    rows, total_count = repo.list_batches(db, client_id=effective_client_id, page=safe_page, page_size=safe_page_size)
    return ReturnIntakeBatchListResponse(
        items=[ReturnIntakeBatchSummaryResponse(**_batch_summary(batch, client)) for batch, client in rows],
        page=safe_page,
        page_size=safe_page_size,
        total_count=total_count,
    ).model_dump()


def get_return_intake_batch(db: Session, auth: AuthContext, batch_id: int) -> dict:
    _require_return_view(auth)
    batch, client = _get_batch_for_auth(db, auth, batch_id)
    return _batch_detail(batch, client)


def paste_return_intake_rows(
    db: Session,
    auth: AuthContext,
    batch_id: int,
    request: ReturnIntakePasteRowsRequest,
) -> dict:
    _require_return_prepare(auth)
    batch, _client = _get_batch_for_auth(db, auth, batch_id)
    existing_count = repo.count_rows(db, batch.id)
    if existing_count > 0 and not request.replace_existing:
        raise _business_error("RETURN_INTAKE_ROWS_ALREADY_EXISTS", "이미 저장된 반품 접수 row가 있습니다.")

    rows: list[ReturnIntakeRow] = []
    for index, item in enumerate(request.rows, start=1):
        row_no = item.row_no or index
        customer_phone_masked = item.customer_phone_masked or _mask_phone(item.customer_phone)
        qty = _safe_int(item.qty)
        raw_data = _build_raw_data(item.model_dump(), customer_phone_masked=customer_phone_masked)
        rows.append(
            ReturnIntakeRow(
                batch_id=batch.id,
                client_id=batch.client_id,
                row_no=row_no,
                order_no=_safe_text(item.order_no),
                return_tracking_no=_safe_text(item.return_tracking_no),
                original_tracking_no=_safe_text(item.original_tracking_no),
                product_code=_safe_text(item.product_code),
                barcode=_safe_text(item.barcode),
                product_name=_safe_text(item.product_name),
                option_name=_safe_text(item.option_name),
                qty=qty,
                return_reason=_safe_text(item.return_reason),
                customer_name=_safe_text(item.customer_name),
                customer_phone_masked=customer_phone_masked,
                raw_data=raw_data,
                validation_status=ROW_VALIDATION_NOT_VALIDATED,
                status=ROW_STATUS_RECEIVED,
            )
        )

    try:
        if request.replace_existing:
            repo.delete_rows_for_batch(db, batch.id)
        repo.create_rows(db, rows)
        repo.update_batch_counts(
            db,
            batch,
            status=BATCH_STATUS_RECEIVED,
            total_rows=len(rows),
            valid_rows=0,
            warning_rows=0,
            error_rows=0,
        )
        db.commit()
        return ReturnIntakePasteRowsResponse(
            batch_id=batch.id,
            saved_row_count=len(rows),
            status=batch.status,
            total_rows=batch.total_rows,
            valid_rows=batch.valid_rows,
            warning_rows=batch.warning_rows,
            error_rows=batch.error_rows,
        ).model_dump()
    except Exception:
        db.rollback()
        raise


def list_return_intake_rows(
    db: Session,
    auth: AuthContext,
    batch_id: int,
    *,
    page: int = 1,
    page_size: int = 200,
) -> dict:
    _require_return_view(auth)
    batch, _client = _get_batch_for_auth(db, auth, batch_id)
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 500)
    rows, total_count = repo.list_rows(db, batch_id=batch.id, page=safe_page, page_size=safe_page_size)
    return ReturnIntakeRowsResponse(
        items=[ReturnIntakeRowResponse(**_row_response(row)) for row in rows],
        page=safe_page,
        page_size=safe_page_size,
        total_count=total_count,
    ).model_dump()


def validate_return_intake_batch(db: Session, auth: AuthContext, batch_id: int) -> dict:
    _require_return_prepare(auth)
    batch, _client = _get_batch_for_auth(db, auth, batch_id)
    rows, total_count = repo.list_rows(db, batch_id=batch.id, page=1, page_size=5000)
    if total_count == 0:
        raise _business_error("RETURN_INTAKE_VALIDATE_NO_ROWS", "검증할 반품 접수 row가 없습니다.")

    valid_rows = 0
    warning_rows = 0
    error_rows = 0

    try:
        for row in rows:
            validation_status, message = _validate_row(db, row)
            if validation_status == ROW_VALIDATION_INVALID:
                error_rows += 1
            elif validation_status == ROW_VALIDATION_WARNING:
                warning_rows += 1
            else:
                valid_rows += 1
            repo.update_row_validation(
                db,
                row,
                validation_status=validation_status,
                validation_message=message,
                status=ROW_STATUS_RECEIVED,
            )

        batch_status = BATCH_STATUS_HAS_ERRORS if error_rows else BATCH_STATUS_VALIDATED
        repo.update_batch_counts(
            db,
            batch,
            status=batch_status,
            total_rows=total_count,
            valid_rows=valid_rows,
            warning_rows=warning_rows,
            error_rows=error_rows,
        )
        db.commit()
        return ReturnIntakeValidateResponse(
            batch_id=batch.id,
            status=batch.status,
            total_rows=batch.total_rows,
            valid_rows=batch.valid_rows,
            warning_rows=batch.warning_rows,
            error_rows=batch.error_rows,
        ).model_dump()
    except Exception:
        db.rollback()
        raise


def prepare_return_intake_batch_for_processing(db: Session, auth: AuthContext, batch_id: int) -> dict:
    _require_return_prepare(auth)
    batch, _client = _get_batch_for_auth(db, auth, batch_id)
    if batch.status not in {
        BATCH_STATUS_VALIDATED,
        BATCH_STATUS_HAS_ERRORS,
        BATCH_STATUS_READY_FOR_PROCESSING,
    }:
        raise _business_error(
            "RETURN_INTAKE_PREPARE_STATUS_INVALID",
            "검증 완료 후 반품처리 대기 대상으로 전환할 수 있습니다.",
        )

    rows = repo.list_rows_for_batch(db, batch.id)
    if not rows:
        raise _business_error("RETURN_INTAKE_PREPARE_NO_ROWS", "전환할 반품 접수 row가 없습니다.")

    prepared_rows = 0
    skipped_rows = 0
    invalid_rows = 0
    warning_rows = 0
    terminal_statuses = {
        ROW_STATUS_READY_FOR_PROCESSING,
        ROW_STATUS_PROCESSING,
        ROW_STATUS_COMPLETED,
        ROW_STATUS_HOLD,
    }

    try:
        for row in rows:
            if row.validation_status == ROW_VALIDATION_INVALID:
                invalid_rows += 1
                continue
            if row.validation_status == ROW_VALIDATION_WARNING:
                warning_rows += 1
            if row.validation_status not in {ROW_VALIDATION_VALID, ROW_VALIDATION_WARNING}:
                skipped_rows += 1
                continue
            if row.status in terminal_statuses:
                skipped_rows += 1
                continue
            row.status = ROW_STATUS_READY_FOR_PROCESSING
            prepared_rows += 1

        if prepared_rows > 0 or skipped_rows > 0:
            repo.update_batch_status(db, batch, status=BATCH_STATUS_READY_FOR_PROCESSING)
        db.commit()
        message = "반품처리 대기 대상으로 전환했습니다."
        if prepared_rows == 0 and skipped_rows > 0:
            message = "이미 전환된 row는 건너뛰었습니다."
        elif prepared_rows == 0 and invalid_rows > 0:
            message = "전환 가능한 정상/경고 row가 없습니다."
        return ReturnIntakePrepareProcessingResponse(
            batch_id=batch.id,
            total_rows=len(rows),
            prepared_rows=prepared_rows,
            skipped_rows=skipped_rows,
            invalid_rows=invalid_rows,
            warning_rows=warning_rows,
            status=batch.status,
            message=message,
        ).model_dump()
    except Exception:
        db.rollback()
        raise


def list_return_processing_tasks(
    db: Session,
    auth: AuthContext,
    *,
    client_id: int | None = None,
    batch_id: int | None = None,
    tracking_no: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict:
    _require_return_view(auth)
    effective_client_id = resolve_effective_client_id(auth, client_id, allow_all_clients=True)
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 500)
    task_status = status or ROW_STATUS_READY_FOR_PROCESSING
    rows, total_count = repo.list_processing_tasks(
        db,
        client_id=effective_client_id,
        batch_id=batch_id,
        tracking_no=_safe_text(tracking_no),
        status=task_status,
        page=safe_page,
        page_size=safe_page_size,
    )
    return ReturnProcessingTaskListResponse(
        items=[ReturnProcessingTaskResponse(**_processing_task_response(row, client)) for row, client in rows],
        page=safe_page,
        page_size=safe_page_size,
        total_count=total_count,
    ).model_dump()


def judge_return_processing_task(
    db: Session,
    auth: AuthContext,
    task_id: int,
    request: ReturnProcessingJudgeRequest,
) -> dict:
    _require_return_prepare(auth)
    task_row = repo.get_processing_task_with_client(db, task_id)
    if task_row is None:
        raise _business_error(
            "RETURN_PROCESSING_TASK_NOT_FOUND",
            "반품처리 작업 대상을 찾을 수 없습니다.",
            404,
        )
    row, client = task_row
    resolve_effective_client_id(auth, row.client_id)

    judgement_status = request.judgement_status.strip().upper()
    if judgement_status not in ALLOWED_JUDGEMENT_STATUSES:
        raise _business_error("RETURN_PROCESSING_JUDGEMENT_INVALID", "지원하지 않는 판정값입니다.")

    if row.validation_status == ROW_VALIDATION_INVALID:
        raise _business_error(
            "RETURN_PROCESSING_TASK_INVALID_VALIDATION",
            "오류 row는 판정을 저장할 수 없습니다.",
        )
    if row.validation_status not in {ROW_VALIDATION_VALID, ROW_VALIDATION_WARNING}:
        raise _business_error(
            "RETURN_PROCESSING_TASK_INVALID_VALIDATION",
            "검증 완료된 정상/경고 row만 판정을 저장할 수 있습니다.",
        )
    if row.status == ROW_STATUS_COMPLETED:
        raise _business_error(
            "RETURN_PROCESSING_TASK_ALREADY_COMPLETED",
            "이미 처리 완료된 항목입니다.",
        )
    if row.status not in {ROW_STATUS_READY_FOR_PROCESSING, ROW_STATUS_PROCESSING}:
        raise _business_error(
            "RETURN_PROCESSING_TASK_INVALID_STATUS",
            "처리 대기 또는 처리 중 상태에서만 판정을 저장할 수 있습니다.",
        )

    _apply_return_judgement(
        row,
        auth,
        judgement_status=judgement_status,
        judgement_memo=request.judgement_memo,
        print_label=request.print_label,
        resolve_hold=False,
    )

    try:
        db.commit()
        db.refresh(row)
        return ReturnProcessingJudgeResponse(
            **_processing_task_response(row, client),
            message="판정을 저장했습니다.",
        ).model_dump()
    except Exception:
        db.rollback()
        raise


def upload_return_processing_attachment(
    db: Session,
    auth: AuthContext,
    task_id: int,
    *,
    filename: str,
    content_type: str | None,
    file_bytes: bytes,
    attachment_type: str | None = None,
    note: str | None = None,
) -> dict:
    _require_return_prepare(auth)
    row, _client = _get_processing_task_for_attachment(db, auth, task_id)
    _ensure_attachment_task_allowed(row)
    safe_filename = _ensure_attachment_filename(filename)
    safe_content_type = _ensure_attachment_content_type(content_type)
    _ensure_attachment_size(file_bytes)
    safe_attachment_type = _ensure_attachment_type(attachment_type)
    extension = Path(safe_filename).suffix.lower()
    stored_filename = f"{uuid4().hex}{extension}"
    relative_path = Path("uploads") / "return-processing" / str(row.client_id) / str(row.id) / stored_filename
    storage_path = RETURN_PROCESSING_UPLOAD_ROOT / str(row.client_id) / str(row.id) / stored_filename

    attachment = ReturnProcessingAttachment(
        return_intake_row_id=row.id,
        client_id=row.client_id,
        batch_id=row.batch_id,
        attachment_type=safe_attachment_type,
        original_filename=safe_filename,
        stored_filename=stored_filename,
        content_type=safe_content_type,
        file_size=len(file_bytes),
        storage_path=relative_path.as_posix(),
        note=_safe_text(note),
        uploaded_by=auth.user_id,
        active_yn=True,
    )

    try:
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage_path.write_bytes(file_bytes)
        repo.create_processing_attachment(db, attachment)
        db.commit()
        db.refresh(attachment)
        return _attachment_response(attachment)
    except Exception:
        db.rollback()
        if storage_path.exists():
            storage_path.unlink()
        raise


def list_return_processing_attachments(
    db: Session,
    auth: AuthContext,
    task_id: int,
    *,
    include_inactive: bool = False,
) -> dict:
    _require_return_view(auth)
    row, _client = _get_processing_task_for_attachment(db, auth, task_id)
    attachments = repo.list_processing_attachments(db, task_id=row.id, include_inactive=include_inactive)
    return ReturnProcessingAttachmentListResponse(
        items=[ReturnProcessingAttachmentResponse(**_attachment_response(attachment)) for attachment in attachments],
    ).model_dump()


def disable_return_processing_attachment(
    db: Session,
    auth: AuthContext,
    task_id: int,
    attachment_id: int,
) -> dict:
    _require_return_prepare(auth)
    row, _client = _get_processing_task_for_attachment(db, auth, task_id)
    attachment = repo.get_processing_attachment(db, task_id=row.id, attachment_id=attachment_id)
    if attachment is None:
        raise _business_error(
            "RETURN_PROCESSING_ATTACHMENT_NOT_FOUND",
            "반품처리 증빙 파일을 찾을 수 없습니다.",
            404,
        )
    try:
        attachment.active_yn = False
        db.commit()
        db.refresh(attachment)
        return _attachment_response(attachment)
    except Exception:
        db.rollback()
        raise


def list_return_closing_candidates(
    db: Session,
    auth: AuthContext,
    *,
    client_id: int | None = None,
    judgement_status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict:
    _require_return_view(auth)
    effective_client_id = resolve_effective_client_id(auth, client_id, allow_all_clients=True)
    safe_judgement_status = _safe_text(judgement_status)
    if safe_judgement_status:
        safe_judgement_status = safe_judgement_status.upper()
        if safe_judgement_status not in ALLOWED_JUDGEMENT_STATUSES:
            raise _business_error("RETURN_CLOSING_JUDGEMENT_INVALID", "지원하지 않는 판정 상태입니다.")
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 500)
    rows, total_count = repo.list_closing_candidates(
        db,
        client_id=effective_client_id,
        judgement_status=safe_judgement_status,
        date_from=date_from,
        date_to=date_to,
        page=safe_page,
        page_size=safe_page_size,
    )
    return ReturnClosingCandidateListResponse(
        items=[ReturnClosingCandidateResponse(**_closing_candidate_response(row, client)) for row, client in rows],
        page=safe_page,
        page_size=safe_page_size,
        total_count=total_count,
    ).model_dump()


def confirm_return_closing(
    db: Session,
    auth: AuthContext,
    request: ReturnClosingConfirmRequest,
) -> dict:
    _require_return_prepare(auth)
    effective_client_id = resolve_effective_client_id(auth, request.client_id, allow_all_clients=True)
    requested_row_ids = list(dict.fromkeys(request.row_ids))
    rows_with_clients = repo.list_closing_rows_by_ids(db, row_ids=requested_row_ids, client_id=effective_client_id)
    found_ids = {row.id for row, _client in rows_with_clients}

    row_results: list[ReturnClosingRowResult] = []
    reflected_rows = 0
    skipped_rows = 0
    failed_rows = 0
    followup_rows = 0
    event_count = 0

    for row_id in requested_row_ids:
        if row_id not in found_ids:
            failed_rows += 1
            row_results.append(
                ReturnClosingRowResult(
                    row_id=row_id,
                    result="FAILED",
                    message="마감 대상 row를 찾을 수 없습니다.",
                )
            )

    try:
        for row, _client in rows_with_clients:
            resolve_effective_client_id(auth, row.client_id)
            if row.inventory_reflected_yn:
                skipped_rows += 1
                row_results.append(
                    ReturnClosingRowResult(
                        row_id=row.id,
                        judgement_status=row.judgement_status,
                        result="SKIPPED",
                        message="이미 재고반영된 row입니다.",
                        inventory_event_id=row.inventory_event_id,
                    )
                )
                continue
            if row.status != ROW_STATUS_COMPLETED or not row.judgement_status:
                failed_rows += 1
                row_results.append(
                    ReturnClosingRowResult(
                        row_id=row.id,
                        judgement_status=row.judgement_status,
                        result="FAILED",
                        message="판정 완료 상태의 row만 마감 확정할 수 있습니다.",
                    )
                )
                continue
            if row.judgement_status != JUDGEMENT_GOOD:
                followup_rows += 1
                row_results.append(
                    ReturnClosingRowResult(
                        row_id=row.id,
                        judgement_status=row.judgement_status,
                        result="FOLLOWUP",
                        message="정상재고 반영 대상이 아니므로 후속 처리 대상으로 남깁니다.",
                    )
                )
                continue
            if row.qty is None or row.qty < 1:
                failed_rows += 1
                row_results.append(
                    ReturnClosingRowResult(
                        row_id=row.id,
                        judgement_status=row.judgement_status,
                        result="FAILED",
                        message="수량이 없어 재고반영할 수 없습니다.",
                    )
                )
                continue

            product = _resolve_return_product(db, row)
            if product is None:
                failed_rows += 1
                row_results.append(
                    ReturnClosingRowResult(
                        row_id=row.id,
                        judgement_status=row.judgement_status,
                        result="FAILED",
                        message="상품 마스터를 찾을 수 없어 재고반영할 수 없습니다.",
                    )
                )
                continue

            warehouse = _resolve_return_good_warehouse(db, row.client_id)
            if warehouse is None:
                failed_rows += 1
                row_results.append(
                    ReturnClosingRowResult(
                        row_id=row.id,
                        judgement_status=row.judgement_status,
                        result="FAILED",
                        message="고객사 기본 반품/입고 창고 설정이 없어 재고반영할 수 없습니다.",
                    )
                )
                continue

            idempotency_key = f"return-closing:{row.id}:good"
            existing_event = inventory_repository.find_event_by_idempotency_key(db, idempotency_key)
            if existing_event is not None:
                row.inventory_reflected_yn = True
                row.inventory_reflected_at = row.inventory_reflected_at or existing_event.created_at
                row.inventory_event_id = existing_event.id
                skipped_rows += 1
                row_results.append(
                    ReturnClosingRowResult(
                        row_id=row.id,
                        judgement_status=row.judgement_status,
                        result="SKIPPED",
                        message="이미 생성된 재고 이벤트가 있어 중복 반영하지 않았습니다.",
                        inventory_event_id=existing_event.id,
                    )
                )
                continue

            event = InventoryEvent(
                event_no=f"RTN-CLOSE-{row.id}",
                client_id=row.client_id,
                warehouse_id=warehouse.id,
                location_id=None,
                product_id=product.id,
                product_code=product.product_code,
                stock_status=RETURN_CLOSING_STOCK_STATUS_GOOD,
                event_type=RETURN_CLOSING_EVENT_TYPE_GOOD_IN,
                qty_delta=row.qty,
                source_type=RETURN_CLOSING_SOURCE_TYPE,
                source_id=row.id,
                source_line_id=row.id,
                idempotency_key=idempotency_key,
                event_reason="반품 양품 일마감 정상재고 반영",
                memo=None,
                created_by=auth.user_id,
                raw_json={
                    "return_intake_row_id": row.id,
                    "batch_id": row.batch_id,
                    "judgement_status": row.judgement_status,
                    "return_management_no": row.return_management_no,
                    "return_label_no": row.return_label_no,
                },
            )
            inventory_repository.create_inventory_event(db, event)
            inventory_repository.increase_current_inventory(
                db,
                client_id=row.client_id,
                warehouse_id=warehouse.id,
                location_id=None,
                product_id=product.id,
                stock_status=RETURN_CLOSING_STOCK_STATUS_GOOD,
                qty_delta=row.qty,
            )
            row.inventory_reflected_yn = True
            row.inventory_reflected_at = datetime.now(timezone.utc)
            row.inventory_event_id = event.id
            reflected_rows += 1
            event_count += 1
            row_results.append(
                ReturnClosingRowResult(
                    row_id=row.id,
                    judgement_status=row.judgement_status,
                    result="REFLECTED",
                    message="정상재고에 반영했습니다.",
                    inventory_event_id=event.id,
                )
            )

        db.commit()
    except Exception:
        db.rollback()
        raise

    return ReturnClosingConfirmResponse(
        total_rows=len(requested_row_ids),
        reflected_rows=reflected_rows,
        skipped_rows=skipped_rows,
        failed_rows=failed_rows,
        followup_rows=followup_rows,
        event_count=event_count,
        message="반품 일마감 처리를 완료했습니다.",
        row_results=row_results,
    ).model_dump()


def list_return_external_outbound_candidates(
    db: Session,
    auth: AuthContext,
    *,
    client_id: int | None = None,
    judgement_status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    return_management_no: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict:
    _require_return_view(auth)
    effective_client_id = resolve_effective_client_id(auth, client_id, allow_all_clients=True)
    safe_judgement_status = _safe_text(judgement_status)
    if safe_judgement_status:
        safe_judgement_status = safe_judgement_status.upper()
        if safe_judgement_status not in EXTERNAL_OUTBOUND_JUDGEMENT_STATUSES:
            raise _business_error(
                "RETURN_EXTERNAL_OUTBOUND_JUDGEMENT_INVALID",
                "외부반출 대상 판정이 아닙니다.",
            )
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 500)
    rows, total_count = repo.list_external_outbound_candidates(
        db,
        outbound_judgement_statuses=EXTERNAL_OUTBOUND_JUDGEMENT_STATUSES,
        confirmed_status=EXTERNAL_OUTBOUND_STATUS_CONFIRMED,
        client_id=effective_client_id,
        judgement_status=safe_judgement_status,
        date_from=date_from,
        date_to=date_to,
        return_management_no=_safe_text(return_management_no),
        page=safe_page,
        page_size=safe_page_size,
    )
    return ReturnExternalOutboundCandidateListResponse(
        items=[
            ReturnExternalOutboundCandidateResponse(**_external_outbound_candidate_response(row, client))
            for row, client in rows
        ],
        page=safe_page,
        page_size=safe_page_size,
        total_count=total_count,
    ).model_dump()


def confirm_return_external_outbound(
    db: Session,
    auth: AuthContext,
    request: ReturnExternalOutboundConfirmRequest,
) -> dict:
    _require_return_prepare(auth)
    effective_client_id = resolve_effective_client_id(auth, request.client_id, allow_all_clients=True)
    requested_row_ids = list(dict.fromkeys(request.row_ids))
    scanned_numbers: set[str] = set()
    for value in request.scanned_numbers or []:
        normalized_value = _normalize_scan_number(value)
        if normalized_value:
            scanned_numbers.add(normalized_value)
    rows_with_clients = repo.list_external_outbound_rows_by_ids(
        db,
        row_ids=requested_row_ids,
        client_id=effective_client_id,
    )
    found_ids = {row.id for row, _client in rows_with_clients}

    row_results: list[ReturnExternalOutboundRowResult] = []
    confirmed_rows = 0
    skipped_rows = 0
    failed_rows = 0

    for row_id in requested_row_ids:
        if row_id not in found_ids:
            failed_rows += 1
            row_results.append(
                ReturnExternalOutboundRowResult(
                    row_id=row_id,
                    result="FAILED",
                    message="외부반출 대상 row를 찾을 수 없습니다.",
                )
            )

    try:
        for row, _client in rows_with_clients:
            resolve_effective_client_id(auth, row.client_id)
            if row.external_outbound_status == EXTERNAL_OUTBOUND_STATUS_CONFIRMED:
                skipped_rows += 1
                row_results.append(
                    ReturnExternalOutboundRowResult(
                        row_id=row.id,
                        judgement_status=row.judgement_status,
                        result="SKIPPED",
                        message="이미 외부반출 확정된 row입니다.",
                        external_outbound_status=row.external_outbound_status,
                    )
                )
                continue
            if row.status != ROW_STATUS_COMPLETED:
                failed_rows += 1
                row_results.append(
                    ReturnExternalOutboundRowResult(
                        row_id=row.id,
                        judgement_status=row.judgement_status,
                        result="FAILED",
                        message="판정 완료된 row만 외부반출 확정할 수 있습니다.",
                        external_outbound_status=row.external_outbound_status,
                    )
                )
                continue
            if row.judgement_status not in EXTERNAL_OUTBOUND_JUDGEMENT_STATUSES:
                failed_rows += 1
                row_results.append(
                    ReturnExternalOutboundRowResult(
                        row_id=row.id,
                        judgement_status=row.judgement_status,
                        result="FAILED",
                        message="외부반출 대상 판정이 아닙니다.",
                        external_outbound_status=row.external_outbound_status,
                    )
                )
                continue
            identifier = _external_outbound_identifier(row)
            if identifier is None:
                failed_rows += 1
                row_results.append(
                    ReturnExternalOutboundRowResult(
                        row_id=row.id,
                        judgement_status=row.judgement_status,
                        result="FAILED",
                        message="반품관리번호 또는 라벨번호가 없어 외부반출 확정할 수 없습니다.",
                        external_outbound_status=row.external_outbound_status,
                    )
                )
                continue
            if scanned_numbers and _normalize_scan_number(identifier) not in scanned_numbers:
                failed_rows += 1
                row_results.append(
                    ReturnExternalOutboundRowResult(
                        row_id=row.id,
                        judgement_status=row.judgement_status,
                        result="FAILED",
                        message="스캔 검수된 번호와 일치하지 않습니다.",
                        external_outbound_status=row.external_outbound_status,
                    )
                )
                continue

            row.external_outbound_required = True
            row.external_outbound_status = EXTERNAL_OUTBOUND_STATUS_CONFIRMED
            row.external_outbound_at = datetime.now(timezone.utc)
            row.external_outbound_confirmed_by = auth.user_id
            confirmed_rows += 1
            row_results.append(
                ReturnExternalOutboundRowResult(
                    row_id=row.id,
                    judgement_status=row.judgement_status,
                    result="CONFIRMED",
                    message="외부반출을 확정했습니다. 현재고는 변경하지 않았습니다.",
                    external_outbound_status=row.external_outbound_status,
                )
            )

        db.commit()
    except Exception:
        db.rollback()
        raise

    return ReturnExternalOutboundConfirmResponse(
        total_rows=len(requested_row_ids),
        confirmed_rows=confirmed_rows,
        skipped_rows=skipped_rows,
        failed_rows=failed_rows,
        message="반품 외부반출 확정 처리를 완료했습니다.",
        row_results=row_results,
    ).model_dump()


def list_return_hold_candidates(
    db: Session,
    auth: AuthContext,
    *,
    client_id: int | None = None,
    hold_status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    return_management_no: str | None = None,
    tracking_no: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict:
    _require_return_view(auth)
    effective_client_id = resolve_effective_client_id(auth, client_id, allow_all_clients=True)
    safe_hold_status = _safe_text(hold_status)
    if safe_hold_status:
        safe_hold_status = safe_hold_status.upper()
        if safe_hold_status not in ALLOWED_HOLD_STATUSES:
            raise _business_error("RETURN_HOLD_STATUS_INVALID", "지원하지 않는 보류 상태입니다.")
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 500)
    rows, total_count = repo.list_hold_candidates(
        db,
        resolved_status=HOLD_STATUS_RESOLVED,
        client_id=effective_client_id,
        hold_status=safe_hold_status,
        date_from=date_from,
        date_to=date_to,
        return_management_no=_safe_text(return_management_no),
        tracking_no=_safe_text(tracking_no),
        page=safe_page,
        page_size=safe_page_size,
    )
    return ReturnHoldCandidateListResponse(
        items=[ReturnHoldCandidateResponse(**_hold_candidate_response(row, client)) for row, client in rows],
        page=safe_page,
        page_size=safe_page_size,
        total_count=total_count,
    ).model_dump()


def update_return_hold_task(
    db: Session,
    auth: AuthContext,
    task_id: int,
    request: ReturnHoldUpdateRequest,
) -> dict:
    _require_return_prepare(auth)
    task_row = repo.get_processing_task_with_client(db, task_id)
    if task_row is None:
        raise _business_error("RETURN_HOLD_TASK_NOT_FOUND", "반품 보류 대상을 찾을 수 없습니다.", 404)
    row, client = task_row
    resolve_effective_client_id(auth, row.client_id)

    if row.judgement_status != JUDGEMENT_HOLD:
        raise _business_error("RETURN_HOLD_INVALID_JUDGEMENT", "HOLD 판정 row만 보류 처리할 수 있습니다.")
    if row.status != ROW_STATUS_COMPLETED:
        raise _business_error("RETURN_HOLD_INVALID_STATUS", "판정 완료된 HOLD row만 보류 처리할 수 있습니다.")

    hold_status = request.hold_status.strip().upper()
    if hold_status not in ALLOWED_HOLD_STATUSES:
        raise _business_error("RETURN_HOLD_STATUS_INVALID", "지원하지 않는 보류 상태입니다.")

    row.hold_status = hold_status
    row.hold_reason = _safe_text(request.hold_reason)
    row.hold_response_memo = _safe_text(request.hold_response_memo)
    if hold_status == HOLD_STATUS_RESOLVED:
        row.hold_resolved_at = datetime.now(timezone.utc)
        row.hold_resolved_by = auth.user_id
    else:
        row.hold_resolved_at = None
        row.hold_resolved_by = None

    try:
        db.commit()
        db.refresh(row)
        return ReturnHoldUpdateResponse(
            **_hold_candidate_response(row, client),
            message="반품 보류 정보를 저장했습니다.",
        ).model_dump()
    except Exception:
        db.rollback()
        raise


def rejudge_return_hold_task(
    db: Session,
    auth: AuthContext,
    task_id: int,
    request: ReturnHoldRejudgeRequest,
) -> dict:
    _require_return_prepare(auth)
    task_row = repo.get_processing_task_with_client(db, task_id)
    if task_row is None:
        raise _business_error("RETURN_HOLD_TASK_NOT_FOUND", "반품 보류 대상을 찾을 수 없습니다.", 404)
    row, client = task_row
    resolve_effective_client_id(auth, row.client_id)

    next_judgement_status = request.judgement_status.strip().upper()
    if next_judgement_status not in ALLOWED_JUDGEMENT_STATUSES:
        raise _business_error("RETURN_HOLD_REJUDGE_STATUS_INVALID", "지원하지 않는 재판정 값입니다.")
    if row.judgement_status != JUDGEMENT_HOLD:
        raise _business_error("RETURN_HOLD_REJUDGE_INVALID_JUDGEMENT", "HOLD 판정 row만 재판정할 수 있습니다.")
    if row.hold_status != HOLD_STATUS_READY_TO_REJUDGE:
        raise _business_error(
            "RETURN_HOLD_REJUDGE_INVALID_HOLD_STATUS",
            "재판정 준비 상태의 HOLD row만 재판정할 수 있습니다.",
        )
    if row.status != ROW_STATUS_COMPLETED:
        raise _business_error(
            "RETURN_HOLD_REJUDGE_INVALID_TASK_STATUS",
            "판정 완료된 HOLD row만 재판정할 수 있습니다.",
        )
    if row.validation_status == ROW_VALIDATION_INVALID:
        raise _business_error(
            "RETURN_HOLD_REJUDGE_INVALID_VALIDATION",
            "오류 row는 재판정할 수 없습니다.",
        )
    if row.validation_status not in {ROW_VALIDATION_VALID, ROW_VALIDATION_WARNING}:
        raise _business_error(
            "RETURN_HOLD_REJUDGE_INVALID_VALIDATION",
            "검증 완료된 정상/경고 row만 재판정할 수 있습니다.",
        )

    response_memo = _safe_text(request.hold_response_memo)
    if response_memo is not None:
        row.hold_response_memo = response_memo

    _apply_return_judgement(
        row,
        auth,
        judgement_status=next_judgement_status,
        judgement_memo=request.judgement_memo,
        print_label=None,
        resolve_hold=True,
    )

    try:
        db.commit()
        db.refresh(row)
        return ReturnHoldRejudgeResponse(
            **_processing_task_response(row, client),
            message=_rejudge_success_message(next_judgement_status),
        ).model_dump()
    except Exception:
        db.rollback()
        raise


def list_return_disposal_candidates(
    db: Session,
    auth: AuthContext,
    *,
    client_id: int | None = None,
    disposal_status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    return_management_no: str | None = None,
    tracking_no: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict:
    _require_return_view(auth)
    effective_client_id = resolve_effective_client_id(auth, client_id, allow_all_clients=True)
    safe_disposal_status = _safe_text(disposal_status)
    if safe_disposal_status:
        safe_disposal_status = safe_disposal_status.upper()
        if safe_disposal_status not in {DISPOSAL_STATUS_PENDING, DISPOSAL_STATUS_CONFIRMED}:
            raise _business_error("RETURN_DISPOSAL_STATUS_INVALID", "지원하지 않는 폐기 상태입니다.")
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 500)
    rows, total_count = repo.list_disposal_candidates(
        db,
        confirmed_status=DISPOSAL_STATUS_CONFIRMED,
        client_id=effective_client_id,
        disposal_status=safe_disposal_status,
        date_from=date_from,
        date_to=date_to,
        return_management_no=_safe_text(return_management_no),
        tracking_no=_safe_text(tracking_no),
        page=safe_page,
        page_size=safe_page_size,
    )
    return ReturnDisposalCandidateListResponse(
        items=[ReturnDisposalCandidateResponse(**_disposal_candidate_response(row, client)) for row, client in rows],
        page=safe_page,
        page_size=safe_page_size,
        total_count=total_count,
    ).model_dump()


def confirm_return_disposal_task(
    db: Session,
    auth: AuthContext,
    task_id: int,
    request: ReturnDisposalConfirmRequest,
) -> dict:
    _require_return_prepare(auth)
    task_row = repo.get_processing_task_with_client(db, task_id)
    if task_row is None:
        raise _business_error("RETURN_DISPOSAL_TASK_NOT_FOUND", "반품 폐기 대상을 찾을 수 없습니다.", 404)
    row, client = task_row
    resolve_effective_client_id(auth, row.client_id)

    if row.judgement_status != JUDGEMENT_DISPOSAL:
        raise _business_error("RETURN_DISPOSAL_INVALID_JUDGEMENT", "DISPOSAL 판정 row만 폐기 확정할 수 있습니다.")
    if row.status != ROW_STATUS_COMPLETED:
        raise _business_error("RETURN_DISPOSAL_INVALID_STATUS", "판정 완료된 DISPOSAL row만 폐기 확정할 수 있습니다.")
    if row.disposal_status == DISPOSAL_STATUS_CONFIRMED:
        raise _business_error("RETURN_DISPOSAL_ALREADY_CONFIRMED", "이미 폐기 확정된 항목입니다.")

    row.disposal_status = DISPOSAL_STATUS_CONFIRMED
    row.disposal_reason = _safe_text(request.disposal_reason)
    row.disposal_memo = _safe_text(request.disposal_memo)
    row.disposal_confirmed_at = datetime.now(timezone.utc)
    row.disposal_confirmed_by = auth.user_id

    try:
        db.commit()
        db.refresh(row)
        return ReturnDisposalConfirmResponse(
            **_disposal_candidate_response(row, client),
            message="반품 폐기를 확정했습니다. 정상재고는 변경하지 않았습니다.",
        ).model_dump()
    except Exception:
        db.rollback()
        raise


def _external_outbound_identifier(row: ReturnIntakeRow) -> str | None:
    return _safe_text(row.return_management_no) or _safe_text(row.return_label_no)


def _normalize_scan_number(value: str | None) -> str | None:
    text = _safe_text(value)
    if text is None:
        return None
    return "".join(text.split()).upper()


def _resolve_return_product(db: Session, row: ReturnIntakeRow):
    if row.product_code:
        product = master_repository.find_product_by_code(db, row.client_id, row.product_code)
        if product is not None and product.active_yn:
            return product

    barcode_norm = _normalize_barcode(row.barcode)
    if barcode_norm:
        product = master_repository.find_product_by_barcode(db, row.client_id, barcode_norm)
        if product is not None and product.active_yn:
            return product
        product_barcode = master_repository.find_product_barcode_by_norm(db, row.client_id, barcode_norm)
        if product_barcode is not None and product_barcode.active_yn:
            product = master_repository.get_product_by_id(db, product_barcode.product_id)
            if product is not None and product.active_yn:
                return product
    return None


def _resolve_return_good_warehouse(db: Session, client_id: int):
    for usage_type in RETURN_GOOD_WAREHOUSE_USAGE_PRIORITY:
        setting = master_repository.find_default_client_warehouse_setting(
            db,
            client_id=client_id,
            usage_type=usage_type,
        )
        if setting is None:
            continue
        warehouse = master_repository.get_warehouse_by_id(db, setting.warehouse_id)
        if warehouse is not None and warehouse.active_yn:
            return warehouse
    return None


def _is_label_print_required(judgement_status: str, print_label: bool | None) -> bool:
    return judgement_status in LABEL_REQUIRED_JUDGEMENT_STATUSES or bool(print_label)


def _apply_return_judgement(
    row: ReturnIntakeRow,
    auth: AuthContext,
    *,
    judgement_status: str,
    judgement_memo: str | None,
    print_label: bool | None,
    resolve_hold: bool,
) -> None:
    label_print_required = _is_label_print_required(judgement_status, print_label)
    if label_print_required:
        next_label_no = row.return_label_no or _generate_return_label_no(row)
        row.return_label_no = next_label_no
        row.return_management_no = row.return_management_no or next_label_no
        row.label_print_status = LABEL_STATUS_LOCAL_AGENT_NOT_CONNECTED
    else:
        row.label_print_status = LABEL_STATUS_NOT_REQUIRED

    now = datetime.now(timezone.utc)
    row.judgement_status = judgement_status
    row.judgement_memo = _safe_text(judgement_memo)
    row.label_print_required = label_print_required
    row.judged_at = now
    row.judged_by = auth.user_id
    row.status = ROW_STATUS_COMPLETED
    if judgement_status in EXTERNAL_OUTBOUND_JUDGEMENT_STATUSES:
        row.external_outbound_required = True
        if row.external_outbound_status != EXTERNAL_OUTBOUND_STATUS_CONFIRMED:
            row.external_outbound_status = EXTERNAL_OUTBOUND_STATUS_READY
    else:
        row.external_outbound_required = False
        if row.external_outbound_status != EXTERNAL_OUTBOUND_STATUS_CONFIRMED:
            row.external_outbound_status = EXTERNAL_OUTBOUND_STATUS_NOT_REQUIRED
    if judgement_status == JUDGEMENT_HOLD:
        row.hold_status = HOLD_STATUS_PENDING
        row.hold_reason = row.hold_reason or row.judgement_memo
        row.hold_resolved_at = None
        row.hold_resolved_by = None
    elif resolve_hold:
        row.hold_status = HOLD_STATUS_RESOLVED
        row.hold_resolved_at = now
        row.hold_resolved_by = auth.user_id
    if judgement_status == JUDGEMENT_DISPOSAL:
        row.disposal_status = DISPOSAL_STATUS_PENDING
        row.disposal_reason = row.disposal_reason or row.judgement_memo
        row.disposal_confirmed_at = None
        row.disposal_confirmed_by = None


def _rejudge_success_message(judgement_status: str) -> str:
    if judgement_status == JUDGEMENT_GOOD:
        return "양품으로 재판정했습니다. 일마감 후보로 이동합니다."
    if judgement_status in EXTERNAL_OUTBOUND_JUDGEMENT_STATUSES:
        return "외부반출 대상 판정으로 재판정했습니다. 외부반출 후보로 이동합니다."
    if judgement_status == JUDGEMENT_DISPOSAL:
        return "폐기로 재판정했습니다. 폐기 후보로 이동합니다."
    if judgement_status == JUDGEMENT_HOLD:
        return "보류 상태를 유지했습니다."
    return "반품 보류 대상을 재판정했습니다."


def _get_processing_task_for_attachment(db: Session, auth: AuthContext, task_id: int):
    task_row = repo.get_processing_task_with_client(db, task_id)
    if task_row is None:
        raise _business_error(
            "RETURN_PROCESSING_ATTACHMENT_TASK_NOT_FOUND",
            "반품처리 작업 대상을 찾을 수 없습니다.",
            404,
        )
    row, client = task_row
    resolve_effective_client_id(auth, row.client_id)
    return row, client


def _ensure_attachment_task_allowed(row: ReturnIntakeRow) -> None:
    if row.validation_status == ROW_VALIDATION_INVALID:
        raise _business_error(
            "RETURN_PROCESSING_ATTACHMENT_TASK_INVALID_VALIDATION",
            "오류 row에는 증빙 파일을 첨부할 수 없습니다.",
        )
    if row.validation_status not in {ROW_VALIDATION_VALID, ROW_VALIDATION_WARNING}:
        raise _business_error(
            "RETURN_PROCESSING_ATTACHMENT_TASK_INVALID_VALIDATION",
            "검증 완료된 정상/경고 row에만 증빙 파일을 첨부할 수 있습니다.",
        )
    if row.status not in {ROW_STATUS_READY_FOR_PROCESSING, ROW_STATUS_PROCESSING, ROW_STATUS_COMPLETED, ROW_STATUS_HOLD}:
        raise _business_error(
            "RETURN_PROCESSING_ATTACHMENT_TASK_INVALID_STATUS",
            "반품처리 대기, 처리 중, 보류, 처리 완료 상태에서만 증빙 파일을 첨부할 수 있습니다.",
        )


def _ensure_attachment_type(value: str | None) -> str:
    normalized = (value or ATTACHMENT_TYPE_PHOTO).strip().upper()
    if normalized not in ALLOWED_ATTACHMENT_TYPES:
        raise _business_error("RETURN_PROCESSING_ATTACHMENT_TYPE_INVALID", "지원하지 않는 증빙 유형입니다.")
    return normalized


def _ensure_attachment_filename(filename: str) -> str:
    safe_filename = Path(filename or "").name.strip()
    if not safe_filename:
        raise _business_error("RETURN_PROCESSING_ATTACHMENT_FILE_REQUIRED", "업로드할 파일이 필요합니다.")
    extension = Path(safe_filename).suffix.lower()
    if extension not in ALLOWED_ATTACHMENT_EXTENSIONS:
        raise _business_error(
            "RETURN_PROCESSING_ATTACHMENT_EXTENSION_INVALID",
            "jpg, jpeg, png, webp 이미지 파일만 첨부할 수 있습니다.",
        )
    return safe_filename


def _ensure_attachment_content_type(content_type: str | None) -> str:
    safe_content_type = (content_type or "").strip().lower()
    if safe_content_type not in ALLOWED_ATTACHMENT_CONTENT_TYPES:
        raise _business_error(
            "RETURN_PROCESSING_ATTACHMENT_CONTENT_TYPE_INVALID",
            "허용되지 않는 이미지 형식입니다.",
        )
    return safe_content_type


def _ensure_attachment_size(file_bytes: bytes) -> None:
    if not file_bytes:
        raise _business_error("RETURN_PROCESSING_ATTACHMENT_FILE_REQUIRED", "업로드할 파일이 필요합니다.")
    if len(file_bytes) > MAX_ATTACHMENT_BYTES:
        raise _business_error(
            "RETURN_PROCESSING_ATTACHMENT_TOO_LARGE",
            "첨부 파일은 10MB 이하만 업로드할 수 있습니다.",
        )


def _generate_return_label_no(row: ReturnIntakeRow) -> str:
    return f"RTN-{datetime.now(timezone.utc):%Y%m%d}-{row.id}"


def _build_raw_data(source: dict[str, Any], *, customer_phone_masked: str | None) -> dict[str, Any]:
    raw_data = dict(source.get("raw_data") or {})
    for key, value in source.items():
        if key in {"raw_data", "customer_phone"}:
            continue
        if value is not None:
            raw_data[key] = value
    if customer_phone_masked:
        raw_data["customer_phone_masked"] = customer_phone_masked
    return raw_data


def _validate_row(db: Session, row: ReturnIntakeRow) -> tuple[str, str | None]:
    errors: list[str] = []
    warnings: list[str] = []

    if not row.order_no and not row.return_tracking_no:
        errors.append("주문번호 또는 반품 운송장번호 중 하나는 필요합니다.")
    if not row.product_code and not row.barcode:
        errors.append("상품코드 또는 바코드 중 하나는 필요합니다.")
    if row.qty is None or row.qty < 1:
        errors.append("수량은 1 이상이어야 합니다.")

    if errors:
        return ROW_VALIDATION_INVALID, " / ".join(errors)

    if not _has_matching_product(db, row.client_id, row.product_code, row.barcode):
        warnings.append("상품마스터에서 상품코드 또는 바코드를 찾지 못했습니다.")

    if warnings:
        return ROW_VALIDATION_WARNING, " / ".join(warnings)
    return ROW_VALIDATION_VALID, None


def _has_matching_product(db: Session, client_id: int, product_code: str | None, barcode: str | None) -> bool:
    if product_code and master_repository.find_product_by_code(db, client_id, product_code):
        return True
    barcode_norm = _normalize_barcode(barcode)
    if not barcode_norm:
        return False
    if master_repository.find_product_by_barcode(db, client_id, barcode_norm):
        return True
    if master_repository.find_product_barcode_by_norm(db, client_id, barcode_norm):
        return True
    return False
