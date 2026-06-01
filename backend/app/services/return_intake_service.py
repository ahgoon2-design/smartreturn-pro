from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.auth_context import resolve_effective_client_id
from app.core.exceptions import AuthError, ClientScopeDeniedError, PermissionDeniedError
from app.core.permissions import can_write, require_permission, require_roles
from app.models.returns import ReturnIntakeRow
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
    ReturnIntakeRowResponse,
    ReturnIntakeRowsResponse,
    ReturnIntakeValidateResponse,
)


BATCH_STATUS_DRAFT = "DRAFT"
BATCH_STATUS_RECEIVED = "RECEIVED"
BATCH_STATUS_VALIDATED = "VALIDATED"
BATCH_STATUS_HAS_ERRORS = "HAS_ERRORS"

ROW_VALIDATION_NOT_VALIDATED = "NOT_VALIDATED"
ROW_VALIDATION_VALID = "VALID"
ROW_VALIDATION_WARNING = "WARNING"
ROW_VALIDATION_INVALID = "INVALID"

ROW_STATUS_RECEIVED = "RECEIVED"
ROW_STATUS_READY_FOR_PROCESSING = "READY_FOR_PROCESSING"

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
        created_at=row.created_at,
        updated_at=row.updated_at,
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
                next_status = ROW_STATUS_RECEIVED
            elif validation_status == ROW_VALIDATION_WARNING:
                warning_rows += 1
                next_status = ROW_STATUS_READY_FOR_PROCESSING
            else:
                valid_rows += 1
                next_status = ROW_STATUS_READY_FOR_PROCESSING
            repo.update_row_validation(
                db,
                row,
                validation_status=validation_status,
                validation_message=message,
                status=next_status,
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
