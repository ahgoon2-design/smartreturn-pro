"""Import job service."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import re
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile

from sqlalchemy.orm import Session

from app.core.auth_context import resolve_effective_client_id
from app.core.exceptions import AuthError, ClientScopeDeniedError
from app.core.permissions import require_permission, require_roles
from app.repositories import master_repository
from app.repositories import import_repository as repo
from app.schemas.auth import AuthContext
from app.schemas.imports import (
    ImportConfirmResponse,
    ImportJobCreateRequest,
    ImportJobDetailResponse,
    ImportJobErrorsResponse,
    ImportExcelUploadResponse,
    ImportJobFileResponse,
    ImportJobListResponse,
    ImportJobRowResponse,
    ImportJobRowsResponse,
    ImportJobSummaryResponse,
    ImportPasteRowsRequest,
    ImportPasteRowsResponse,
    ImportValidationRunRequest,
    ImportValidationRunResponse,
    ImportValidationErrorResponse,
)


ALLOWED_IMPORT_TYPES = {
    "PRODUCT_MASTER",
    "PRODUCT_BARCODE",
    "RETURN_EXPECTED",
    "RETURN_RECEPTION",
    "INBOUND_EXPECTED",
    "OUTBOUND_ORDER",
}

ALLOWED_SOURCE_TYPES = {
    "EXCEL_FILE",
    "PASTE",
    "MANUAL",
}

PASTE_ROW_SOURCE_TYPES = {"PASTE", "MANUAL"}
EXCEL_FILE_SOURCE_TYPES = {"EXCEL_FILE"}
VALIDATION_SOURCE_TYPES = {"PASTE", "MANUAL", "EXCEL_FILE"}
VALIDATION_READY_STATUS = "READY_TO_VALIDATE"
VALIDATION_COMPLETED_STATUSES = {"VALIDATED", "HAS_ERRORS"}
IMPORT_APPLIED_STATUS = "APPLIED"
EXCEL_UPLOAD_READY_STATUS = "DRAFT"
EXCEL_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
DEFAULT_IMPORT_BARCODE_TYPE = "EACH"

EXCEL_HEADER_MAP = {
    "product_code": "product_code",
    "product code": "product_code",
    "상품코드": "product_code",
    "product_name": "product_name",
    "product name": "product_name",
    "상품명": "product_name",
    "barcode": "barcode",
    "bar_code": "barcode",
    "바코드": "barcode",
    "barcode_type": "barcode_type",
    "barcode type": "barcode_type",
    "바코드유형": "barcode_type",
    "unit_qty": "unit_qty",
    "unit qty": "unit_qty",
    "수량": "unit_qty",
    "단위수량": "unit_qty",
}


@dataclass(frozen=True)
class ParsedExcelRows:
    worksheet_name: str
    headers: list[str]
    rows: list[dict]


def _business_error(result_code: str, message: str, status_code: int = 400) -> AuthError:
    return AuthError(message, result_code=result_code, status_code=status_code)


def _safe_page(page: int) -> int:
    return max(page, 1)


def _safe_page_size(page_size: int) -> int:
    return min(max(page_size, 1), 200)


def _require_import_view(auth: AuthContext) -> None:
    require_permission(auth, "IMPORT_VIEW")


def _require_import_manage(auth: AuthContext) -> None:
    require_roles(auth, {"SUPER_ADMIN", "INTERNAL_ADMIN"})
    require_permission(auth, "IMPORT_MANAGE")


def _ensure_import_type(import_type: str) -> str:
    value = import_type.strip()
    if value not in ALLOWED_IMPORT_TYPES:
        raise _business_error("IMPORT_JOB_IMPORT_TYPE_INVALID", "지원하지 않는 import_type 입니다.")
    return value


def _ensure_source_type(source_type: str) -> str:
    value = source_type.strip()
    if value not in ALLOWED_SOURCE_TYPES:
        raise _business_error("IMPORT_JOB_SOURCE_TYPE_INVALID", "지원하지 않는 source_type 입니다.")
    return value


def _ensure_paste_source_type(source_type: str) -> None:
    if source_type not in PASTE_ROW_SOURCE_TYPES:
        raise _business_error(
            "IMPORT_JOB_PASTE_SOURCE_TYPE_INVALID",
            "Paste row ??ν? PASTE ?먮뒗 MANUAL source_type?먯꽌留??덉슜?⑸땲??",
        )


def _ensure_validation_source_type(source_type: str) -> None:
    if source_type not in VALIDATION_SOURCE_TYPES:
        raise _business_error(
            "IMPORT_JOB_VALIDATE_SOURCE_TYPE_INVALID",
            "Import validation supports only PASTE, MANUAL, or uploaded EXCEL_FILE source_type.",
        )


def _ensure_excel_source_type(source_type: str) -> None:
    if source_type not in EXCEL_FILE_SOURCE_TYPES:
        raise _business_error(
            "IMPORT_JOB_EXCEL_UPLOAD_SOURCE_TYPE_INVALID",
            "Excel file upload supports only EXCEL_FILE source_type.",
        )


def extract_multipart_file(body: bytes, content_type: str) -> tuple[str, str | None, bytes]:
    """Extract the `file` part without adding python-multipart as a runtime dependency."""

    boundary_match = re.search(r'boundary="?([^";]+)"?', content_type or "")
    if not boundary_match:
        raise _business_error("IMPORT_JOB_EXCEL_FILE_REQUIRED", "Excel file is required.")

    boundary = f"--{boundary_match.group(1)}".encode("latin-1")
    for part in body.split(boundary):
        if not part or part in {b"--", b"--\r\n"}:
            continue
        part = part.lstrip(b"\r\n")
        if part.endswith(b"--"):
            part = part[:-2]
        header_bytes, separator, content = part.partition(b"\r\n\r\n")
        if not separator:
            continue
        headers_text = header_bytes.decode("latin-1", errors="replace")
        if 'name="file"' not in headers_text:
            continue
        file_name_match = re.search(r'filename="([^"]*)"', headers_text)
        file_name = file_name_match.group(1).strip() if file_name_match else ""
        if not file_name:
            raise _business_error("IMPORT_JOB_EXCEL_FILE_REQUIRED", "Excel file is required.")
        mime_type_match = re.search(r"content-type:\s*([^\r\n]+)", headers_text, re.IGNORECASE)
        mime_type = mime_type_match.group(1).strip() if mime_type_match else None
        if content.endswith(b"\r\n"):
            content = content[:-2]
        if not content:
            raise _business_error("IMPORT_JOB_EXCEL_FILE_REQUIRED", "Excel file is required.")
        return file_name, mime_type, content

    raise _business_error("IMPORT_JOB_EXCEL_FILE_REQUIRED", "Excel file is required.")


def _ensure_xlsx_file(file_name: str, file_bytes: bytes) -> None:
    if not file_name.lower().endswith(".xlsx"):
        raise _business_error("IMPORT_JOB_EXCEL_FILE_TYPE_INVALID", "Only .xlsx files are supported.")
    if len(file_bytes) > EXCEL_MAX_FILE_SIZE_BYTES:
        raise _business_error("IMPORT_JOB_EXCEL_FILE_TOO_LARGE", "Excel file is too large.")


def _normalize_excel_header(header: str) -> str | None:
    key = " ".join(str(header).strip().lower().replace("-", "_").split())
    return EXCEL_HEADER_MAP.get(key)


def _xml_text(element: ET.Element) -> str:
    return "".join(element.itertext())


def _read_shared_strings(zip_file: ZipFile) -> list[str]:
    try:
        shared_xml = zip_file.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(shared_xml)
    return [_xml_text(item) for item in root.iter() if item.tag.endswith("}si") or item.tag == "si"]


def _first_sheet_name(zip_file: ZipFile) -> str:
    try:
        workbook_xml = zip_file.read("xl/workbook.xml")
    except KeyError:
        return "Sheet1"
    root = ET.fromstring(workbook_xml)
    for item in root.iter():
        if item.tag.endswith("}sheet") or item.tag == "sheet":
            return item.attrib.get("name") or "Sheet1"
    return "Sheet1"


def _cell_column_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha()).upper()
    value = 0
    for char in letters:
        value = value * 26 + (ord(char) - ord("A") + 1)
    return max(value - 1, 0)


def _read_cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return _xml_text(cell).strip()
    value_node = next((child for child in cell if child.tag.endswith("}v") or child.tag == "v"), None)
    if value_node is None or value_node.text is None:
        return ""
    text = value_node.text.strip()
    if cell_type == "s":
        try:
            return shared_strings[int(text)].strip()
        except (IndexError, ValueError):
            return ""
    return text


def _parse_xlsx_rows(file_bytes: bytes) -> ParsedExcelRows:
    try:
        with ZipFile(BytesIO(file_bytes)) as zip_file:
            worksheet_paths = sorted(
                path
                for path in zip_file.namelist()
                if path.startswith("xl/worksheets/sheet") and path.endswith(".xml")
            )
            if not worksheet_paths:
                raise _business_error("IMPORT_JOB_EXCEL_WORKSHEET_NOT_FOUND", "Excel worksheet was not found.")

            worksheet_name = _first_sheet_name(zip_file)
            shared_strings = _read_shared_strings(zip_file)
            sheet_root = ET.fromstring(zip_file.read(worksheet_paths[0]))
    except BadZipFile:
        raise _business_error("IMPORT_JOB_EXCEL_FILE_INVALID", "Excel file is invalid.") from None
    except ET.ParseError:
        raise _business_error("IMPORT_JOB_EXCEL_FILE_INVALID", "Excel file is invalid.") from None

    parsed_rows: list[tuple[int, list[str]]] = []
    for row in sheet_root.iter():
        if not (row.tag.endswith("}row") or row.tag == "row"):
            continue
        row_no = int(row.attrib.get("r") or len(parsed_rows) + 1)
        values: dict[int, str] = {}
        for cell in row:
            if not (cell.tag.endswith("}c") or cell.tag == "c"):
                continue
            values[_cell_column_index(cell.attrib.get("r", ""))] = _read_cell_value(cell, shared_strings)
        if values:
            max_index = max(values)
            parsed_rows.append((row_no, [values.get(index, "") for index in range(max_index + 1)]))

    if not parsed_rows:
        raise _business_error("IMPORT_JOB_EXCEL_HEADERS_REQUIRED", "Excel header row is required.")

    _header_row_no, header_values = parsed_rows[0]
    headers = [header.strip() for header in header_values]
    if not any(headers):
        raise _business_error("IMPORT_JOB_EXCEL_HEADERS_REQUIRED", "Excel header row is required.")

    rows: list[dict] = []
    for row_no, values in parsed_rows[1:]:
        if not any(value.strip() for value in values):
            continue
        raw_json: dict[str, str] = {}
        normalized_json: dict[str, str] = {}
        for index, header in enumerate(headers):
            if not header:
                continue
            value = values[index].strip() if index < len(values) else ""
            raw_json[header] = value
            normalized_key = _normalize_excel_header(header)
            if normalized_key:
                normalized_json[normalized_key] = value
        rows.append(
            {
                "row_no": row_no,
                "raw_json": raw_json,
                "normalized_json": normalized_json or None,
                "source_row_key": f"{worksheet_name}!{row_no}",
            }
        )

    if not rows:
        raise _business_error("IMPORT_JOB_EXCEL_NO_ROWS", "Excel file has no data rows.")

    return ParsedExcelRows(worksheet_name=worksheet_name, headers=headers, rows=rows)


def _ensure_requested_client(db: Session, client_id: int):
    client = master_repository.get_client_by_id(db, client_id)
    if client is None:
        raise _business_error("MASTER_CLIENT_NOT_FOUND", "고객사를 찾을 수 없습니다.", 404)
    if not client.active_yn:
        raise _business_error("MASTER_CLIENT_INACTIVE", "비활성 고객사에는 import job을 생성할 수 없습니다.")
    return client


def _ensure_requested_warehouse(db: Session, warehouse_id: int):
    warehouse = master_repository.get_warehouse_by_id(db, warehouse_id)
    if warehouse is None:
        raise _business_error("MASTER_WAREHOUSE_NOT_FOUND", "창고를 찾을 수 없습니다.", 404)
    if not warehouse.active_yn:
        raise _business_error("MASTER_WAREHOUSE_INACTIVE", "비활성 창고에는 import job을 생성할 수 없습니다.")
    return warehouse


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


def _normalize_paste_rows(request: ImportPasteRowsRequest) -> list[dict]:
    if request.replace_existing:
        raise _business_error("IMPORT_JOB_REPLACE_UNSUPPORTED", "replace_existing? 1李?skeleton?먯꽌 吏?먰븯吏 ?딆뒿?덈떎.")
    if not request.rows:
        raise _business_error("IMPORT_JOB_ROWS_REQUIRED", "Import row媛 ?꾩슂?⑸땲??")

    normalized_rows: list[dict] = []
    seen_row_nos: set[int] = set()
    for index, row in enumerate(request.rows, start=1):
        row_no = row.row_no if row.row_no is not None else index
        if row_no < 1:
            raise _business_error("IMPORT_JOB_ROW_NO_INVALID", "row_no??1 ?댁긽?댁뼱???⑸땲??")
        if row_no in seen_row_nos:
            raise _business_error("IMPORT_JOB_ROW_NO_DUPLICATED", "以묐났??row_no媛 ?덉뒿?덈떎.")
        seen_row_nos.add(row_no)
        normalized_rows.append(
            {
                "row_no": row_no,
                "raw_json": row.raw_json,
                "normalized_json": row.normalized_json,
                "source_row_key": row.source_row_key,
            }
        )
    return normalized_rows


def _raw_value(value) -> str | None:
    if value is None:
        return None
    text = str(value)
    if len(text) > 200:
        return f"{text[:200]}..."
    return text


def _is_blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _issue(
    *,
    field_name: str | None,
    raw_value,
    error_code: str,
    error_message: str,
    severity: str = "ERROR",
) -> dict:
    return {
        "field_name": field_name,
        "raw_value": _raw_value(raw_value),
        "error_code": error_code,
        "error_message": error_message,
        "severity": severity,
    }


def _required_field(data: dict, field_name: str) -> list[dict]:
    if _is_blank(data.get(field_name)):
        return [
            _issue(
                field_name=field_name,
                raw_value=data.get(field_name),
                error_code="REQUIRED_FIELD_MISSING",
                error_message=f"{field_name} is required.",
            )
        ]
    return []


def _required_one_of(data: dict, field_names: tuple[str, ...]) -> list[dict]:
    if any(not _is_blank(data.get(field_name)) for field_name in field_names):
        return []
    return [
        _issue(
            field_name=",".join(field_names),
            raw_value=None,
            error_code="REQUIRED_ONE_OF_MISSING",
            error_message=f"One of {', '.join(field_names)} is required.",
        )
    ]


def _number_min_if_present(
    data: dict,
    field_name: str,
    *,
    min_value: float,
    required: bool = False,
) -> list[dict]:
    value = data.get(field_name)
    if _is_blank(value):
        return _required_field(data, field_name) if required else []
    if isinstance(value, bool):
        return [
            _issue(
                field_name=field_name,
                raw_value=value,
                error_code="INVALID_NUMBER",
                error_message=f"{field_name} must be a number.",
            )
        ]
    try:
        number = float(value)
    except (TypeError, ValueError):
        return [
            _issue(
                field_name=field_name,
                raw_value=value,
                error_code="INVALID_NUMBER",
                error_message=f"{field_name} must be a number.",
            )
        ]
    if number < min_value:
        return [
            _issue(
                field_name=field_name,
                raw_value=value,
                error_code="INVALID_MIN_VALUE",
                error_message=f"{field_name} must be at least {min_value:g}.",
            )
        ]
    return []


def _row_data(row) -> dict:
    if isinstance(row.normalized_json, dict) and row.normalized_json:
        return row.normalized_json
    if isinstance(row.raw_json, dict):
        return row.raw_json
    return {}


def _text_value(data: dict, field_name: str) -> str | None:
    value = data.get(field_name)
    if _is_blank(value):
        return None
    return str(value).strip()


def _normalize_barcode_value(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _int_value_or_default(data: dict, field_name: str, default: int) -> int:
    value = data.get(field_name)
    if _is_blank(value):
        return default
    try:
        number = int(float(str(value).strip()))
    except (TypeError, ValueError):
        raise _business_error("INVALID_NUMBER", f"{field_name} must be a number.")
    if number < 1:
        raise _business_error("INVALID_MIN_VALUE", f"{field_name} must be at least 1.")
    return number


def _barcode_exists(db: Session, *, client_id: int, barcode: str | None) -> bool:
    barcode_norm = _normalize_barcode_value(barcode)
    if barcode_norm is None:
        return False
    return bool(
        master_repository.find_product_by_barcode(db, client_id, barcode_norm)
        or master_repository.find_product_barcode_by_norm(db, client_id, barcode_norm)
    )


def _create_barcode_if_missing(
    db: Session,
    *,
    client_id: int,
    product_id: int,
    barcode: str | None,
    barcode_type: str | None,
    unit_qty: int,
) -> tuple[bool, int | None]:
    barcode_norm = _normalize_barcode_value(barcode)
    if barcode_norm is None:
        return False, None
    if _barcode_exists(db, client_id=client_id, barcode=barcode_norm):
        return False, None
    product_barcode = master_repository.create_product_barcode(
        db,
        client_id=client_id,
        product_id=product_id,
        barcode=barcode_norm,
        barcode_norm=barcode_norm,
        barcode_type=barcode_type or DEFAULT_IMPORT_BARCODE_TYPE,
        unit_qty=unit_qty,
    )
    return True, product_barcode.id


def _validate_product_master(data: dict) -> list[dict]:
    issues = []
    issues.extend(_required_field(data, "product_code"))
    issues.extend(_required_field(data, "product_name"))
    if _is_blank(data.get("barcode")):
        issues.append(
            _issue(
                field_name="barcode",
                raw_value=data.get("barcode"),
                error_code="PRODUCT_BARCODE_MISSING",
                error_message="barcode is missing.",
                severity="WARNING",
            )
        )
    return issues


def _validate_product_barcode(data: dict) -> list[dict]:
    issues = []
    issues.extend(_required_field(data, "product_code"))
    issues.extend(_required_field(data, "barcode"))
    issues.extend(_number_min_if_present(data, "unit_qty", min_value=1))
    return issues


def _validate_return_reception(data: dict) -> list[dict]:
    issues = []
    issues.extend(_required_one_of(data, ("tracking_no", "invoice_no")))
    issues.extend(_required_one_of(data, ("product_code", "barcode")))
    return issues


def _validate_return_expected(data: dict) -> list[dict]:
    return _required_one_of(data, ("tracking_no", "invoice_no"))


def _validate_inbound_expected(data: dict) -> list[dict]:
    issues = []
    issues.extend(_required_field(data, "product_code"))
    issues.extend(_number_min_if_present(data, "expected_qty", min_value=1, required=True))
    return issues


def _validate_outbound_order(data: dict) -> list[dict]:
    issues = []
    issues.extend(_required_one_of(data, ("order_no", "tracking_no")))
    issues.extend(_required_field(data, "product_code"))
    return issues


def _validate_import_row(import_type: str, data: dict) -> list[dict]:
    validators = {
        "PRODUCT_MASTER": _validate_product_master,
        "PRODUCT_BARCODE": _validate_product_barcode,
        "RETURN_RECEPTION": _validate_return_reception,
        "RETURN_EXPECTED": _validate_return_expected,
        "INBOUND_EXPECTED": _validate_inbound_expected,
        "OUTBOUND_ORDER": _validate_outbound_order,
    }
    return validators[import_type](data)


def _validation_status(issues: list[dict]) -> str:
    if any(issue["severity"] == "ERROR" for issue in issues):
        return "INVALID"
    if any(issue["severity"] == "WARNING" for issue in issues):
        return "WARNING"
    return "VALID"


def _validation_message(issues: list[dict]) -> str | None:
    for severity in ("ERROR", "WARNING"):
        for issue in issues:
            if issue["severity"] == severity:
                return issue["error_message"]
    return None


def create_import_job(db: Session, auth: AuthContext, request: ImportJobCreateRequest) -> dict:
    _require_import_manage(auth)
    if request.requested_client_id is None:
        raise _business_error("IMPORT_JOB_REQUESTED_CLIENT_REQUIRED", "requested_client_id는 필수입니다.")
    requested_client_id = resolve_effective_client_id(auth, request.requested_client_id)

    import_type = _ensure_import_type(request.import_type)
    source_type = _ensure_source_type(request.source_type)
    _ensure_requested_client(db, requested_client_id)
    if request.requested_warehouse_id is not None:
        _ensure_requested_warehouse(db, request.requested_warehouse_id)

    try:
        job = repo.create_import_job(
            db,
            import_type=import_type,
            source_type=source_type,
            source_name=request.source_name,
            requested_client_id=requested_client_id,
            requested_warehouse_id=request.requested_warehouse_id,
            file_name=request.file_name,
            worksheet_name=request.worksheet_name,
            message=request.message,
            raw_json=request.raw_json,
            created_by=auth.user_id,
        )
        db.commit()
        row = repo.get_import_job(db, job.id)
        if row is None:
            raise _business_error("IMPORT_JOB_NOT_FOUND", "생성된 import job을 찾을 수 없습니다.", 404)
        created_job, client, warehouse = row
        files = repo.list_import_job_files(db, job_id=created_job.id)
        return _job_detail(created_job, client, warehouse, files).model_dump()
    except Exception:
        db.rollback()
        raise


def save_paste_import_job_rows(
    db: Session,
    auth: AuthContext,
    *,
    job_id: int,
    request: ImportPasteRowsRequest,
) -> dict:
    _require_import_manage(auth)
    row = repo.get_import_job(db, job_id)
    if row is None:
        raise _business_error("IMPORT_JOB_NOT_FOUND", "Import job??李얠쓣 ???놁뒿?덈떎.", 404)
    job, _, _ = row
    _ensure_job_access(auth, job)
    _ensure_paste_source_type(job.source_type)

    rows = _normalize_paste_rows(request)
    if repo.count_import_job_rows(db, job_id=job.id) > 0:
        raise _business_error("IMPORT_JOB_ROWS_ALREADY_EXISTS", "湲곗〈 row媛 ?덈뒗 import job?먮뒗 paste row瑜????????놁뒿?덈떎.")

    try:
        repo.bulk_create_import_job_rows(
            db,
            job_id=job.id,
            client_id=job.requested_client_id,
            rows=rows,
        )
        updated_job = repo.update_import_job_after_rows_saved(
            db,
            job=job,
            row_count=len(rows),
            source_name=request.source_name,
            worksheet_name=request.worksheet_name,
        )
        db.commit()
        return ImportPasteRowsResponse(
            job_id=updated_job.id,
            saved_row_count=len(rows),
            status=updated_job.status,
            total_rows=updated_job.total_rows,
            parsed_rows=updated_job.parsed_rows,
            valid_rows=updated_job.valid_rows,
            invalid_rows=updated_job.invalid_rows,
            error_rows=updated_job.error_rows,
            progress_percent=updated_job.progress_percent,
        ).model_dump()
    except Exception:
        db.rollback()
        raise


def upload_excel_import_job_file(
    db: Session,
    auth: AuthContext,
    *,
    job_id: int,
    file_name: str,
    mime_type: str | None,
    file_bytes: bytes,
) -> dict:
    _require_import_manage(auth)
    row = repo.get_import_job(db, job_id)
    if row is None:
        raise _business_error("IMPORT_JOB_NOT_FOUND", "Import job was not found.", 404)
    job, _, _ = row
    _ensure_job_access(auth, job)
    _ensure_excel_source_type(job.source_type)
    if job.status != EXCEL_UPLOAD_READY_STATUS:
        raise _business_error("IMPORT_JOB_EXCEL_UPLOAD_STATUS_INVALID", "Import job is not ready for Excel upload.")
    if repo.count_import_job_rows(db, job_id=job.id) > 0:
        raise _business_error("IMPORT_JOB_ROWS_ALREADY_EXISTS", "Import job already has rows.")

    _ensure_xlsx_file(file_name, file_bytes)
    parsed = _parse_xlsx_rows(file_bytes)

    try:
        repo.create_import_job_file(
            db,
            job_id=job.id,
            file_name=file_name,
            stored_file_name=None,
            relative_path=None,
            mime_type=mime_type,
            size_bytes=len(file_bytes),
            uploaded_by=auth.user_id,
        )
        repo.bulk_create_import_job_rows(
            db,
            job_id=job.id,
            client_id=job.requested_client_id,
            rows=parsed.rows,
        )
        updated_job = repo.update_import_job_after_rows_saved(
            db,
            job=job,
            row_count=len(parsed.rows),
            source_name=file_name,
            worksheet_name=parsed.worksheet_name,
        )
        updated_job.file_name = file_name
        updated_job.raw_json = {"headers": parsed.headers, "worksheet_name": parsed.worksheet_name}
        db.flush()
        db.commit()
        return ImportExcelUploadResponse(
            job_id=updated_job.id,
            saved_row_count=len(parsed.rows),
            status=updated_job.status,
            total_rows=updated_job.total_rows,
            parsed_rows=updated_job.parsed_rows,
            valid_rows=updated_job.valid_rows,
            invalid_rows=updated_job.invalid_rows,
            error_rows=updated_job.error_rows,
            progress_percent=updated_job.progress_percent,
            file_name=file_name,
            worksheet_name=parsed.worksheet_name,
            headers=parsed.headers,
        ).model_dump()
    except Exception:
        db.rollback()
        raise


def validate_import_job(
    db: Session,
    auth: AuthContext,
    *,
    job_id: int,
    request: ImportValidationRunRequest,
) -> dict:
    _require_import_manage(auth)
    if request.force:
        raise _business_error("IMPORT_JOB_VALIDATE_FORCE_UNSUPPORTED", "force validation is not supported.")

    row = repo.get_import_job(db, job_id)
    if row is None:
        raise _business_error("IMPORT_JOB_NOT_FOUND", "Import job was not found.", 404)
    job, _, _ = row
    _ensure_job_access(auth, job)
    _ensure_validation_source_type(job.source_type)
    if job.status in VALIDATION_COMPLETED_STATUSES:
        raise _business_error("IMPORT_JOB_VALIDATE_ALREADY_DONE", "Import job validation is already completed.")
    if job.status != VALIDATION_READY_STATUS:
        raise _business_error("IMPORT_JOB_VALIDATE_STATUS_INVALID", "Import job is not ready to validate.")
    if repo.has_existing_validation_errors(db, job_id=job.id):
        raise _business_error("IMPORT_JOB_VALIDATE_ALREADY_DONE", "Import job already has validation errors.")

    rows = repo.list_import_job_rows_for_validation(db, job_id=job.id)
    if not rows:
        raise _business_error("IMPORT_JOB_VALIDATE_NO_ROWS", "Import job has no rows to validate.")
    if any(row_item.validation_status != "NOT_VALIDATED" for row_item in rows):
        raise _business_error("IMPORT_JOB_VALIDATE_ALREADY_DONE", "Import job rows are already validated.")

    try:
        validation_errors: list[dict] = []
        valid_rows = 0
        invalid_rows = 0
        warning_rows = 0
        error_row_ids: set[int] = set()

        for row_item in rows:
            issues = _validate_import_row(job.import_type, _row_data(row_item))
            status = _validation_status(issues)
            if status == "INVALID":
                invalid_rows += 1
            else:
                valid_rows += 1
                if status == "WARNING":
                    warning_rows += 1

            if any(issue["severity"] == "ERROR" for issue in issues):
                error_row_ids.add(row_item.id)

            repo.update_import_job_row_validation(
                db,
                row=row_item,
                validation_status=status,
                validation_message=_validation_message(issues),
            )
            for issue in issues:
                validation_errors.append(
                    {
                        "job_id": job.id,
                        "row_id": row_item.id,
                        "row_no": row_item.row_no,
                        "field_name": issue["field_name"],
                        "raw_value": issue["raw_value"],
                        "error_code": issue["error_code"],
                        "error_message": issue["error_message"],
                        "severity": issue["severity"],
                    }
                )

        if validation_errors:
            repo.bulk_create_import_validation_errors(db, errors=validation_errors)

        status = "HAS_ERRORS" if invalid_rows > 0 else "VALIDATED"
        updated_job = repo.update_import_job_after_validation(
            db,
            job=job,
            status=status,
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            error_rows=len(error_row_ids),
            message=(
                f"validation completed: valid={valid_rows}, invalid={invalid_rows}, "
                f"warning={warning_rows}, errors={len(validation_errors)}"
            ),
        )
        db.commit()
        return ImportValidationRunResponse(
            job_id=updated_job.id,
            status=updated_job.status,
            total_rows=updated_job.total_rows,
            validated_row_count=len(rows),
            valid_rows=updated_job.valid_rows,
            invalid_rows=updated_job.invalid_rows,
            warning_rows=warning_rows,
            error_rows=updated_job.error_rows,
            validation_error_count=len(validation_errors),
            progress_percent=updated_job.progress_percent,
        ).model_dump()
    except Exception:
        db.rollback()
        raise


def _apply_product_master_row(db: Session, *, client_id: int, row_item) -> tuple[str, int | None, str | None]:
    data = _row_data(row_item)
    product_code = _text_value(data, "product_code")
    product_name = _text_value(data, "product_name")
    barcode = _text_value(data, "barcode")
    barcode_type = _text_value(data, "barcode_type")
    if not product_code or not product_name:
        return "FAILED", None, "REQUIRED_FIELD_MISSING"

    product = master_repository.find_product_by_code(db, client_id, product_code)
    created_product = False
    if product is None:
        product = master_repository.create_product(
            db,
            client_id=client_id,
            product_code=product_code,
            product_name=product_name,
            barcode=None,
        )
        created_product = True

    created_barcode = False
    if barcode:
        created_barcode, _barcode_id = _create_barcode_if_missing(
            db,
            client_id=client_id,
            product_id=product.id,
            barcode=barcode,
            barcode_type=barcode_type,
            unit_qty=1,
        )

    if created_product or created_barcode:
        return "APPLIED", product.id, None
    return "SKIPPED", product.id, None


def _apply_product_barcode_row(db: Session, *, client_id: int, row_item) -> tuple[str, int | None, str | None]:
    data = _row_data(row_item)
    product_code = _text_value(data, "product_code")
    barcode = _text_value(data, "barcode")
    barcode_type = _text_value(data, "barcode_type") or DEFAULT_IMPORT_BARCODE_TYPE
    if not product_code or not barcode:
        return "FAILED", None, "REQUIRED_FIELD_MISSING"

    product = master_repository.find_product_by_code(db, client_id, product_code)
    if product is None:
        return "FAILED", None, "PRODUCT_NOT_FOUND"

    unit_qty = _int_value_or_default(data, "unit_qty", 1)
    created_barcode, barcode_id = _create_barcode_if_missing(
        db,
        client_id=client_id,
        product_id=product.id,
        barcode=barcode,
        barcode_type=barcode_type,
        unit_qty=unit_qty,
    )
    if created_barcode:
        return "APPLIED", barcode_id, None
    return "SKIPPED", product.id, None


def confirm_import_job(db: Session, auth: AuthContext, *, job_id: int) -> dict:
    _require_import_manage(auth)
    row = repo.get_import_job(db, job_id)
    if row is None:
        raise _business_error("IMPORT_JOB_NOT_FOUND", "Import job was not found.", 404)
    job, _, _ = row
    _ensure_job_access(auth, job)

    if job.status in {IMPORT_APPLIED_STATUS, "CONFIRMED", "IMPORTED"}:
        raise _business_error("IMPORT_JOB_CONFIRM_ALREADY_DONE", "Import job is already confirmed.")
    if job.status == "HAS_ERRORS":
        raise _business_error("IMPORT_JOB_CONFIRM_HAS_ERRORS", "Import job has invalid rows.")
    if job.status != "VALIDATED":
        raise _business_error("IMPORT_JOB_CONFIRM_STATUS_INVALID", "Import job is not ready to confirm.")
    if job.import_type not in {"PRODUCT_MASTER", "PRODUCT_BARCODE"}:
        raise _business_error("IMPORT_JOB_CONFIRM_UNSUPPORTED_TYPE", "Import type is not supported for confirm.")
    if job.requested_client_id is None:
        raise _business_error("IMPORT_JOB_REQUESTED_CLIENT_REQUIRED", "requested_client_id is required.")

    rows = repo.list_import_job_rows_for_validation(db, job_id=job.id)
    if not rows:
        raise _business_error("IMPORT_JOB_CONFIRM_NO_ROWS", "Import job has no rows to confirm.")
    if any(row_item.validation_status == "INVALID" for row_item in rows) or job.invalid_rows > 0:
        raise _business_error("IMPORT_JOB_CONFIRM_HAS_ERRORS", "Import job has invalid rows.")

    try:
        applied_rows = 0
        skipped_rows = 0
        failed_rows = 0
        failure_errors: list[dict] = []

        for row_item in rows:
            if row_item.validation_status not in {"VALID", "WARNING"}:
                row_item.target_action = "FAILED"
                failed_rows += 1
                failure_errors.append(
                    {
                        "job_id": job.id,
                        "row_id": row_item.id,
                        "row_no": row_item.row_no,
                        "field_name": None,
                        "raw_value": None,
                        "error_code": "IMPORT_ROW_NOT_VALIDATED",
                        "error_message": "Row is not validated.",
                        "severity": "ERROR",
                    }
                )
                continue

            if job.import_type == "PRODUCT_MASTER":
                action, target_id, error_code = _apply_product_master_row(
                    db,
                    client_id=job.requested_client_id,
                    row_item=row_item,
                )
                row_item.target_table = "products"
            else:
                action, target_id, error_code = _apply_product_barcode_row(
                    db,
                    client_id=job.requested_client_id,
                    row_item=row_item,
                )
                row_item.target_table = "product_barcodes"

            row_item.target_action = action
            row_item.target_id = target_id
            if action == "APPLIED":
                applied_rows += 1
            elif action == "SKIPPED":
                skipped_rows += 1
            else:
                failed_rows += 1
                failure_errors.append(
                    {
                        "job_id": job.id,
                        "row_id": row_item.id,
                        "row_no": row_item.row_no,
                        "field_name": None,
                        "raw_value": None,
                        "error_code": error_code or "IMPORT_JOB_CONFIRM_ROW_FAILED",
                        "error_message": "Row could not be applied.",
                        "severity": "ERROR",
                    }
                )

        if failure_errors:
            repo.bulk_create_import_validation_errors(db, errors=failure_errors)

        warning_rows = sum(1 for row_item in rows if row_item.validation_status == "WARNING")
        next_status = "FAILED" if failed_rows > 0 else IMPORT_APPLIED_STATUS
        result_code = "IMPORT_JOB_CONFIRM_PARTIAL_FAILED" if failed_rows > 0 else "IMPORT_JOB_CONFIRMED"
        message = (
            f"confirm completed: applied={applied_rows}, skipped={skipped_rows}, "
            f"failed={failed_rows}, warnings={warning_rows}"
        )
        updated_job = repo.update_import_job_after_confirm(
            db,
            job=job,
            status=next_status,
            inserted_rows=applied_rows,
            updated_rows=0,
            skipped_rows=skipped_rows,
            error_rows=failed_rows,
            message=message,
        )
        db.commit()
        return ImportConfirmResponse(
            job_id=updated_job.id,
            import_type=updated_job.import_type,
            source_type=updated_job.source_type,
            status=updated_job.status,
            total_rows=updated_job.total_rows,
            applied_rows=applied_rows,
            skipped_rows=skipped_rows,
            failed_rows=failed_rows,
            warning_rows=warning_rows,
            invalid_rows=updated_job.invalid_rows,
            result_code=result_code,
            message=message,
        ).model_dump()
    except Exception:
        db.rollback()
        raise


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
