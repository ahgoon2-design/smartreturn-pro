"""Import job service."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import re
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.core.auth_context import resolve_effective_client_id
from app.core.exceptions import AuthError, ClientScopeDeniedError
from app.core.permissions import require_permission, require_roles
from app.repositories import master_repository
from app.repositories import import_repository as repo
from app.schemas.auth import AuthContext
from app.schemas.imports import (
    ImportAutoMapRequest,
    ImportCanonicalFieldResponse,
    ImportConfirmResponse,
    ImportMappingApplyRequest,
    ImportMappingProfileCreateRequest,
    ImportMappingProfileResponse,
    ImportMappingProfilesResponse,
    ImportMappingResponse,
    ImportMappingSuggestionItem,
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
    ImportSourceTypeResponse,
)


ALLOWED_IMPORT_TYPES = {
    "CLIENT_MASTER",
    "COMMON_CODE",
    "CLIENT_WAREHOUSE",
    "CLIENT_UNIT",
    "RETURN_WAREHOUSE_ROUTE",
    "RETURN_INTAKE",
    "PRODUCT_MASTER",
    "PRODUCT_BARCODE",
    "RETURN_EXPECTED",
    "RETURN_RECEPTION",
    "INBOUND_EXPECTED",
    "OUTBOUND_ORDER",
}

ALLOWED_SOURCE_TYPES = {
    "CSV_FILE",
    "EXCEL_FILE",
    "PASTE",
    "MANUAL",
    "GOOGLE_SHEET",
    "API",
}

PASTE_ROW_SOURCE_TYPES = {"PASTE", "MANUAL", "CSV_FILE"}
EXCEL_FILE_SOURCE_TYPES = {"EXCEL_FILE"}
VALIDATION_SOURCE_TYPES = {"PASTE", "MANUAL", "EXCEL_FILE", "CSV_FILE"}
VALIDATION_READY_STATUS = "READY_TO_VALIDATE"
VALIDATION_COMPLETED_STATUSES = {"VALIDATED", "HAS_ERRORS"}
IMPORT_APPLIED_STATUS = "APPLIED"
EXCEL_UPLOAD_READY_STATUS = "DRAFT"
EXCEL_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
DEFAULT_IMPORT_BARCODE_TYPE = "EACH"

CANONICAL_FIELDS: dict[str, list[dict]] = {
    "PRODUCT_MASTER": [
        {"field_name": "client_code", "label": "고객사코드", "required": False},
        {"field_name": "client_name", "label": "고객사명", "required": False},
        {"field_name": "product_code", "label": "상품코드", "required": True},
        {"field_name": "product_name", "label": "상품명", "required": True},
        {"field_name": "option_name", "label": "옵션명", "required": False},
        {"field_name": "primary_barcode", "label": "대표바코드", "required": False},
        {"field_name": "additional_barcode", "label": "추가바코드", "required": False},
        {"field_name": "carton_barcode", "label": "카톤바코드", "required": False},
        {"field_name": "unit_qty", "label": "카톤입수", "required": False},
        {"field_name": "is_active", "label": "사용여부", "required": False},
        {"field_name": "memo", "label": "메모", "required": False},
    ],
    "PRODUCT_BARCODE": [
        {"field_name": "product_code", "label": "상품코드", "required": True},
        {"field_name": "barcode", "label": "바코드", "required": True},
        {"field_name": "barcode_type", "label": "바코드유형", "required": False},
        {"field_name": "unit_qty", "label": "입수", "required": False},
    ],
    "CLIENT_MASTER": [
        {"field_name": "client_code", "label": "고객사코드", "required": True},
        {"field_name": "client_name", "label": "고객사명", "required": True},
        {"field_name": "business_no", "label": "사업자번호", "required": False},
        {"field_name": "representative_name", "label": "대표자명", "required": False},
        {"field_name": "phone", "label": "전화번호", "required": False},
        {"field_name": "address", "label": "주소", "required": False},
        {"field_name": "is_active", "label": "사용여부", "required": False},
        {"field_name": "memo", "label": "메모", "required": False},
    ],
    "COMMON_CODE": [
        {"field_name": "group_code", "label": "그룹코드", "required": True},
        {"field_name": "code", "label": "코드", "required": True},
        {"field_name": "code_name", "label": "코드명", "required": True},
        {"field_name": "sort_order", "label": "정렬순서", "required": False},
        {"field_name": "is_active", "label": "사용여부", "required": False},
        {"field_name": "memo", "label": "메모", "required": False},
    ],
    "CLIENT_WAREHOUSE": [
        {"field_name": "client_code", "label": "고객사코드", "required": False},
        {"field_name": "client_name", "label": "고객사명", "required": False},
        {"field_name": "warehouse_code", "label": "창고코드", "required": True},
        {"field_name": "warehouse_name", "label": "창고명", "required": True},
        {"field_name": "warehouse_type", "label": "창고유형", "required": False},
        {"field_name": "is_default_inbound", "label": "기본입고", "required": False},
        {"field_name": "is_default_outbound", "label": "기본출고", "required": False},
        {"field_name": "is_default_return", "label": "기본반품", "required": False},
        {"field_name": "is_active", "label": "사용여부", "required": False},
        {"field_name": "memo", "label": "메모", "required": False},
    ],
    "CLIENT_UNIT": [
        {"field_name": "client_code", "label": "고객사코드", "required": False},
        {"field_name": "client_name", "label": "고객사명", "required": False},
        {"field_name": "unit_code", "label": "팀코드", "required": True},
        {"field_name": "unit_name", "label": "팀명", "required": True},
        {"field_name": "sort_order", "label": "정렬순서", "required": False},
        {"field_name": "is_active", "label": "사용여부", "required": False},
        {"field_name": "memo", "label": "메모", "required": False},
    ],
    "RETURN_WAREHOUSE_ROUTE": [
        {"field_name": "client_code", "label": "고객사코드", "required": False},
        {"field_name": "client_name", "label": "고객사명", "required": False},
        {"field_name": "unit_code", "label": "팀코드", "required": False},
        {"field_name": "unit_name", "label": "팀명", "required": False},
        {"field_name": "judgment_code", "label": "판정코드", "required": True},
        {"field_name": "warehouse_code", "label": "창고코드", "required": True},
        {"field_name": "warehouse_name", "label": "창고명", "required": False},
        {"field_name": "is_active", "label": "사용여부", "required": False},
        {"field_name": "memo", "label": "메모", "required": False},
    ],
    "RETURN_INTAKE": [
        {"field_name": "tracking_no", "label": "운송장번호", "required": True},
        {"field_name": "order_no", "label": "주문번호", "required": False},
        {"field_name": "product_code", "label": "상품코드", "required": False},
        {"field_name": "product_barcode", "label": "상품바코드", "required": False},
        {"field_name": "product_name", "label": "상품명", "required": False},
        {"field_name": "option_name", "label": "옵션명", "required": False},
        {"field_name": "qty", "label": "수량", "required": False},
        {"field_name": "customer_name", "label": "고객명", "required": False},
        {"field_name": "return_reason", "label": "반품사유", "required": False},
        {"field_name": "client_unit_code", "label": "팀코드", "required": False},
        {"field_name": "client_unit_name", "label": "팀명", "required": False},
    ],
    "RETURN_EXPECTED": [
        {"field_name": "tracking_no", "label": "운송장번호", "required": True},
        {"field_name": "product_code", "label": "상품코드", "required": False},
        {"field_name": "barcode", "label": "바코드", "required": False},
    ],
    "RETURN_RECEPTION": [
        {"field_name": "tracking_no", "label": "운송장번호", "required": True},
        {"field_name": "product_code", "label": "상품코드", "required": False},
        {"field_name": "barcode", "label": "바코드", "required": False},
    ],
    "INBOUND_EXPECTED": [
        {"field_name": "product_code", "label": "상품코드", "required": True},
        {"field_name": "expected_qty", "label": "입고예정수량", "required": True},
    ],
    "OUTBOUND_ORDER": [
        {"field_name": "order_no", "label": "주문번호", "required": False},
        {"field_name": "tracking_no", "label": "운송장번호", "required": False},
        {"field_name": "product_code", "label": "상품코드", "required": True},
    ],
}

HEADER_ALIASES = {
    "client_code": ("client_code", "고객사코드", "고객사 코드", "거래처코드", "업체코드"),
    "client_name": ("client_name", "고객사명", "고객사", "거래처명", "업체명"),
    "product_code": (
        "product_code",
        "product code",
        "상품코드",
        "상품 코드",
        "품목코드",
        "품목 코드",
        "제품코드",
        "제품 코드",
        "SKU",
        "sku",
        "옵션코드",
        "옵션 코드",
    ),
    "product_name": (
        "product_name",
        "product name",
        "상품명",
        "상품 명",
        "품목명",
        "품목 명",
        "제품명",
        "제품 명",
        "상품명(옵션명)",
        "상품명/옵션명",
        "옵션명",
    ),
    "option_name": ("option_name", "옵션명", "옵션", "규격", "색상/사이즈", "사이즈", "색상"),
    "primary_barcode": (
        "primary_barcode",
        "barcode",
        "bar_code",
        "대표바코드",
        "대표 바코드",
        "바코드",
        "바코드번호",
        "바코드 번호",
        "상품바코드",
        "상품 바코드",
        "EAN",
        "JAN",
    ),
    "barcode": (
        "barcode",
        "bar_code",
        "바코드",
        "바코드번호",
        "바코드 번호",
        "상품바코드",
        "상품 바코드",
        "대표바코드",
        "대표 바코드",
    ),
    "additional_barcode": ("additional_barcode", "추가바코드", "추가 바코드", "보조바코드", "별도바코드"),
    "carton_barcode": ("carton_barcode", "카톤바코드", "카톤 바코드", "박스바코드", "박스코드", "carton barcode"),
    "barcode_type": (
        "barcode_type",
        "barcode type",
        "바코드유형",
        "바코드 유형",
        "바코드타입",
        "바코드 타입",
    ),
    "unit_qty": (
        "unit_qty",
        "unit qty",
        "수량",
        "단위수량",
        "단위 수량",
        "입수",
        "구성수량",
        "구성 수량",
        "묶음수량",
        "묶음 수량",
        "카톤입수",
        "박스입수",
        "박스수량",
        "수량/박스",
    ),
    "is_active": ("is_active", "사용여부", "상태", "활성여부", "사용 여부"),
    "memo": ("memo", "메모", "비고", "설명"),
    "business_no": ("business_no", "사업자번호", "사업자 번호"),
    "representative_name": ("representative_name", "대표자명", "대표자"),
    "phone": ("phone", "전화번호", "연락처"),
    "address": ("address", "주소"),
    "group_code": ("group_code", "그룹코드", "공통코드그룹"),
    "code": ("code", "코드", "공통코드"),
    "code_name": ("code_name", "코드명", "코드 이름", "명칭"),
    "sort_order": ("sort_order", "정렬순서", "정렬", "순서"),
    "warehouse_code": ("warehouse_code", "창고코드", "창고 코드"),
    "warehouse_name": ("warehouse_name", "창고명", "창고 이름", "창고"),
    "warehouse_type": ("warehouse_type", "창고유형", "창고 타입"),
    "is_default_inbound": ("is_default_inbound", "기본입고", "입고기본"),
    "is_default_outbound": ("is_default_outbound", "기본출고", "출고기본"),
    "is_default_return": ("is_default_return", "기본반품", "반품기본"),
    "unit_code": ("unit_code", "팀코드", "운영단위코드", "부서코드"),
    "unit_name": ("unit_name", "팀명", "운영단위", "운영단위명", "부서명"),
    "judgment_code": ("judgment_code", "판정코드", "판정상태", "판정"),
    "tracking_no": ("tracking_no", "운송장번호", "송장번호", "송장", "택배번호"),
    "order_no": ("order_no", "주문번호", "주문 번호", "주문ID"),
    "product_barcode": ("product_barcode", "상품바코드", "상품 바코드", "바코드"),
    "qty": ("qty", "수량", "반품수량"),
    "customer_name": ("customer_name", "고객명", "수취인", "주문자"),
    "return_reason": ("return_reason", "반품사유", "사유"),
    "client_unit_code": ("client_unit_code", "팀코드", "운영단위코드"),
    "client_unit_name": ("client_unit_name", "팀명", "운영단위명"),
    "expected_qty": ("expected_qty", "입고예정수량", "예정수량"),
}

EXCEL_COMPAT_HEADER_ALIASES = {
    "product_code": HEADER_ALIASES["product_code"],
    "product_name": (
        "product_name",
        "product name",
        "상품명",
        "상품 명",
        "품목명",
        "품목 명",
        "제품명",
        "제품 명",
        "상품명(옵션명)",
        "상품명/옵션명",
        "옵션명",
    ),
    "barcode": HEADER_ALIASES["primary_barcode"],
    "barcode_type": HEADER_ALIASES["barcode_type"],
    "unit_qty": HEADER_ALIASES["unit_qty"],
}


def _excel_header_lookup_key(header: str) -> str:
    return "".join(ch for ch in str(header).strip().lower() if ch not in {" ", "\t", "\n", "\r", "_", "-", "/", "(", ")"})


EXCEL_COMPAT_HEADER_MAP = {
    _excel_header_lookup_key(alias): standard_key
    for standard_key, aliases in EXCEL_COMPAT_HEADER_ALIASES.items()
    for alias in aliases
}

MEANINGLESS_VALUE_TOKENS = {
    "",
    "-",
    "--",
    "---",
    "―",
    "—",
    "n/a",
    "na",
    "none",
    "null",
    "없음",
    "해당없음",
    "해당 없음",
}

NOISE_ROW_KEYWORDS = {
    "합계",
    "총계",
    "소계",
    "total",
    "subtotal",
    "grand total",
    "메모",
    "비고",
    "주의",
    "주의사항",
    "안내",
    "설명",
    "note",
    "remark",
}

DATA_ROW_CORE_FIELDS = {
    "PRODUCT_MASTER": ("product_code", "product_name", "primary_barcode", "barcode", "additional_barcode", "carton_barcode"),
    "CLIENT_MASTER": ("client_name", "client_code", "business_no"),
    "COMMON_CODE": ("group_code", "code", "code_name"),
    "CLIENT_WAREHOUSE": ("warehouse_name", "warehouse_code", "client_name", "client_code"),
    "CLIENT_UNIT": ("unit_name", "unit_code", "client_name", "client_code"),
    "RETURN_WAREHOUSE_ROUTE": ("judgment_code", "warehouse_name", "warehouse_code", "client_name", "client_code"),
    "RETURN_INTAKE": ("tracking_no", "order_no", "product_code", "product_barcode", "product_name"),
    "PRODUCT_BARCODE": ("product_code", "barcode"),
    "RETURN_RECEPTION": ("tracking_no", "invoice_no", "product_code", "barcode"),
    "RETURN_EXPECTED": ("tracking_no", "invoice_no"),
    "INBOUND_EXPECTED": ("product_code", "expected_qty"),
    "OUTBOUND_ORDER": ("order_no", "tracking_no", "product_code"),
}


@dataclass(frozen=True)
class ParsedExcelRows:
    worksheet_name: str
    headers: list[str]
    mapped_headers: dict[str, str]
    unmapped_headers: list[str]
    rows: list[dict]
    skipped_empty_rows: int = 0
    skipped_noise_rows: int = 0


@dataclass(frozen=True)
class FilteredImportRows:
    rows: list[dict]
    skipped_empty_rows: int
    skipped_noise_rows: int


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


def _canonical_field_names(import_type: str) -> set[str]:
    return {field["field_name"] for field in CANONICAL_FIELDS.get(import_type, [])}


def _required_field_names(import_type: str) -> set[str]:
    return {field["field_name"] for field in CANONICAL_FIELDS.get(import_type, []) if field.get("required")}


def _header_alias_lookup(import_type: str) -> dict[str, str]:
    field_names = _canonical_field_names(import_type)
    lookup: dict[str, str] = {}
    for field_name in field_names:
        aliases = HEADER_ALIASES.get(field_name, (field_name,))
        for alias in aliases:
            lookup[_excel_header_lookup_key(alias)] = field_name
        lookup[_excel_header_lookup_key(field_name)] = field_name
    return lookup


def _headers_signature(headers: list[str]) -> str:
    return "|".join(_excel_header_lookup_key(header) for header in headers if str(header).strip())


def _collect_headers(rows) -> list[str]:
    headers: list[str] = []
    for row in rows:
        raw_json = row.raw_json if hasattr(row, "raw_json") else row.get("raw_json")
        if not isinstance(raw_json, dict):
            continue
        for header in raw_json:
            if header not in headers:
                headers.append(header)
    return headers


def _build_mapping_suggestions(import_type: str, headers: list[str], profile_mapping: dict | None = None) -> tuple[dict[str, str], list[dict]]:
    field_names = _canonical_field_names(import_type)
    alias_lookup = _header_alias_lookup(import_type)
    profile_mapping = profile_mapping or {}
    applied_mapping: dict[str, str] = {}
    suggestions: list[dict] = []
    target_counts: dict[str, int] = {}

    for header in headers:
        clean_header = str(header).strip()
        if not clean_header:
            continue
        target_field = None
        confidence = 0.0
        status = "UNMAPPED"
        profile_target = profile_mapping.get(clean_header)
        if isinstance(profile_target, str) and profile_target in field_names:
            target_field = profile_target
            confidence = 0.98
            status = "PROFILE"
        else:
            lookup_key = _excel_header_lookup_key(clean_header)
            alias_target = alias_lookup.get(lookup_key)
            if alias_target:
                target_field = alias_target
                confidence = 1.0 if lookup_key == _excel_header_lookup_key(alias_target) else 0.93
                status = "AUTO"

        if target_field:
            target_counts[target_field] = target_counts.get(target_field, 0) + 1
            if target_counts[target_field] == 1:
                applied_mapping[clean_header] = target_field
            else:
                status = "AMBIGUOUS"
                applied_mapping.pop(clean_header, None)

        suggestions.append(
            {
                "source_header": clean_header,
                "target_field": target_field,
                "confidence": round(confidence, 2),
                "status": status,
            }
        )

    duplicated_targets = {target for target, count in target_counts.items() if count > 1}
    if duplicated_targets:
        applied_mapping = {
            source_header: target_field
            for source_header, target_field in applied_mapping.items()
            if target_field not in duplicated_targets
        }
        for suggestion in suggestions:
            if suggestion["target_field"] in duplicated_targets:
                suggestion["status"] = "AMBIGUOUS"

    return applied_mapping, suggestions


def _apply_header_mapping(raw_json: dict, mapping: dict[str, str]) -> dict:
    mapped: dict[str, object] = {}
    for source_header, value in raw_json.items():
        target_field = mapping.get(source_header)
        if target_field:
            mapped[target_field] = value
    if "primary_barcode" in mapped and "barcode" not in mapped:
        mapped["barcode"] = mapped["primary_barcode"]
    if "barcode" in mapped and "primary_barcode" not in mapped:
        mapped["primary_barcode"] = mapped["barcode"]
    return mapped


def _clean_cell_value(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.startswith("="):
        return ""
    return text


def _is_meaningful_value(value) -> bool:
    text = _clean_cell_value(value)
    if not text:
        return False
    return text.lower() not in MEANINGLESS_VALUE_TOKENS


def _is_noise_only_value(value) -> bool:
    text = _clean_cell_value(value).lower()
    if not text:
        return False
    return any(keyword in text for keyword in NOISE_ROW_KEYWORDS)


def _canonicalized_row_for_filter(import_type: str, row: dict) -> dict:
    raw_json = row.get("raw_json")
    normalized_json = row.get("normalized_json")
    if isinstance(normalized_json, dict) and normalized_json:
        data = dict(normalized_json)
    elif isinstance(raw_json, dict):
        headers = list(raw_json)
        mapping, _suggestions = _build_mapping_suggestions(import_type, headers)
        data = _apply_header_mapping(raw_json, mapping)
    else:
        data = {}
    if "barcode" in data and "primary_barcode" not in data:
        data["primary_barcode"] = data["barcode"]
    if "primary_barcode" in data and "barcode" not in data:
        data["barcode"] = data["primary_barcode"]
    return data


def _is_empty_import_row(row: dict) -> bool:
    raw_json = row.get("raw_json")
    if not isinstance(raw_json, dict) or not raw_json:
        return True
    return not any(_clean_cell_value(value) for value in raw_json.values())


def _is_noise_import_row(import_type: str, row: dict) -> bool:
    data = _canonicalized_row_for_filter(import_type, row)
    core_fields = DATA_ROW_CORE_FIELDS.get(import_type, tuple(_required_field_names(import_type)))
    core_values = [_clean_cell_value(data.get(field_name)) for field_name in core_fields if _is_meaningful_value(data.get(field_name))]
    if not core_values:
        return True
    return all(_is_noise_only_value(value) for value in core_values)


def _filter_actual_import_rows(import_type: str, rows: list[dict]) -> FilteredImportRows:
    kept_rows: list[dict] = []
    skipped_empty_rows = 0
    skipped_noise_rows = 0
    for row in rows:
        if _is_empty_import_row(row):
            skipped_empty_rows += 1
            continue
        if _is_noise_import_row(import_type, row):
            skipped_noise_rows += 1
            continue
        kept_rows.append(row)
    return FilteredImportRows(
        rows=kept_rows,
        skipped_empty_rows=skipped_empty_rows,
        skipped_noise_rows=skipped_noise_rows,
    )


def _row_filter_summary(filtered: FilteredImportRows) -> dict:
    return {
        "skipped_empty_rows": filtered.skipped_empty_rows,
        "skipped_noise_rows": filtered.skipped_noise_rows,
    }


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


def _normalize_excel_header(header: str, import_type: str) -> str | None:
    return EXCEL_COMPAT_HEADER_MAP.get(_excel_header_lookup_key(header))


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


def _parse_xlsx_rows(file_bytes: bytes, import_type: str) -> ParsedExcelRows:
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

    mapped_headers: dict[str, str] = {}
    unmapped_headers: list[str] = []
    header_mappings: list[str | None] = []
    for header in headers:
        if not header:
            header_mappings.append(None)
            continue
        normalized_key = _normalize_excel_header(header, import_type)
        if normalized_key and normalized_key not in mapped_headers:
            mapped_headers[normalized_key] = header
            header_mappings.append(normalized_key)
        else:
            unmapped_headers.append(header)
            header_mappings.append(None)

    rows: list[dict] = []
    for row_no, values in parsed_rows[1:]:
        raw_json: dict[str, str] = {}
        normalized_json: dict[str, str] = {}
        for index, header in enumerate(headers):
            if not header:
                continue
            value = values[index].strip() if index < len(values) else ""
            raw_json[header] = value
            normalized_key = header_mappings[index]
            if normalized_key:
                normalized_json[normalized_key] = value
        if "primary_barcode" in normalized_json and "barcode" not in normalized_json:
            normalized_json["barcode"] = normalized_json["primary_barcode"]
        if "barcode" in normalized_json and "primary_barcode" not in normalized_json:
            normalized_json["primary_barcode"] = normalized_json["barcode"]
        rows.append(
            {
                "row_no": row_no,
                "raw_json": raw_json,
                "normalized_json": normalized_json or None,
                "source_row_key": f"{worksheet_name}!{row_no}",
            }
        )

    filtered = _filter_actual_import_rows(import_type, rows)

    if not filtered.rows:
        raise _business_error("IMPORT_JOB_EXCEL_NO_ROWS", "Excel file has no data rows.")

    return ParsedExcelRows(
        worksheet_name=worksheet_name,
        headers=headers,
        mapped_headers=mapped_headers,
        unmapped_headers=unmapped_headers,
        rows=filtered.rows,
        skipped_empty_rows=filtered.skipped_empty_rows,
        skipped_noise_rows=filtered.skipped_noise_rows,
    )


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


def _profile_response(profile) -> ImportMappingProfileResponse:
    return ImportMappingProfileResponse(
        profile_id=profile.id,
        client_id=profile.client_id,
        import_type=profile.import_type,
        source_type=profile.source_type,
        profile_name=profile.profile_name,
        header_signature=profile.header_signature,
        mapping_json=profile.mapping_json,
        active_yn=profile.active_yn,
        last_used_at=profile.last_used_at,
        created_by=profile.created_by,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _ensure_job_access(auth: AuthContext, job) -> None:
    if job.requested_client_id is None:
        if auth.is_internal_user:
            return
        raise ClientScopeDeniedError("고객사 범위가 지정되지 않은 import job은 내부 운영자만 조회할 수 있습니다.")
    resolve_effective_client_id(auth, job.requested_client_id)


def list_import_source_types(db: Session, auth: AuthContext) -> dict:
    _require_import_view(auth)
    return ImportSourceTypeResponse(
        import_types=sorted(ALLOWED_IMPORT_TYPES),
        source_types=sorted(ALLOWED_SOURCE_TYPES),
    ).model_dump()


def get_import_source_type_fields(db: Session, auth: AuthContext, import_type: str) -> dict:
    _require_import_view(auth)
    safe_import_type = _ensure_import_type(import_type)
    fields = []
    for field in CANONICAL_FIELDS.get(safe_import_type, []):
        field_name = field["field_name"]
        fields.append(
            ImportCanonicalFieldResponse(
                field_name=field_name,
                label=field["label"],
                required=bool(field.get("required")),
                aliases=list(HEADER_ALIASES.get(field_name, (field_name,))),
            )
        )
    return {"import_type": safe_import_type, "fields": [field.model_dump() for field in fields]}


def _latest_matching_profile(db: Session, *, job, header_signature: str):
    profiles = repo.list_import_mapping_profiles(
        db,
        client_id=job.requested_client_id,
        import_type=job.import_type,
        source_type=job.source_type,
        header_signature=header_signature,
        active_only=True,
    )
    return profiles[0] if profiles else None


def _mapping_response_from_job(db: Session, *, job, rows, mapping: dict[str, str], suggestions: list[dict]) -> ImportMappingResponse:
    headers = _collect_headers(rows)
    header_signature = _headers_signature(headers)
    ambiguous_headers = [item["source_header"] for item in suggestions if item["status"] == "AMBIGUOUS"]
    unmapped_headers = [item["source_header"] for item in suggestions if item["status"] == "UNMAPPED"]
    low_confidence_headers = [
        item["source_header"]
        for item in suggestions
        if item["target_field"] and item["confidence"] < 0.9 and item["status"] != "AMBIGUOUS"
    ]
    required_missing_fields = sorted(_required_field_names(job.import_type) - set(mapping.values()))
    confirmation_required = bool(ambiguous_headers or unmapped_headers or low_confidence_headers or required_missing_fields)
    return ImportMappingResponse(
        job_id=job.id,
        import_type=job.import_type,
        source_type=job.source_type,
        header_signature=header_signature,
        applied_mapping=mapping,
        suggestions=[ImportMappingSuggestionItem(**item) for item in suggestions],
        mapped_rows=len(rows),
        confirmation_required=confirmation_required,
        low_confidence_headers=low_confidence_headers,
        ambiguous_headers=ambiguous_headers,
        unmapped_headers=unmapped_headers,
        required_missing_fields=required_missing_fields,
    )


def _save_mapping_profile_if_requested(
    db: Session,
    auth: AuthContext,
    *,
    job,
    header_signature: str,
    mapping: dict[str, str],
    save_profile: bool,
    profile_name: str | None,
):
    if not save_profile:
        return None
    safe_profile_name = (profile_name or f"{job.import_type} 기본 매핑").strip()
    return repo.create_or_update_import_mapping_profile(
        db,
        client_id=job.requested_client_id,
        import_type=job.import_type,
        source_type=job.source_type,
        profile_name=safe_profile_name,
        header_signature=header_signature,
        mapping_json=mapping,
        created_by=auth.user_id,
    )


def auto_map_import_job(db: Session, auth: AuthContext, *, job_id: int, request: ImportAutoMapRequest) -> dict:
    _require_import_manage(auth)
    row = repo.get_import_job(db, job_id)
    if row is None:
        raise _business_error("IMPORT_JOB_NOT_FOUND", "Import job을 찾을 수 없습니다.", 404)
    job, _, _ = row
    _ensure_job_access(auth, job)
    rows = repo.list_import_job_rows_for_validation(db, job_id=job.id)
    if not rows:
        raise _business_error("IMPORT_JOB_MAPPING_NO_ROWS", "매핑할 row가 없습니다.")
    headers = _collect_headers(rows)
    header_signature = _headers_signature(headers)
    profile = _latest_matching_profile(db, job=job, header_signature=header_signature)
    mapping, suggestions = _build_mapping_suggestions(
        job.import_type,
        headers,
        profile.mapping_json if profile else None,
    )
    response = _mapping_response_from_job(db, job=job, rows=rows, mapping=mapping, suggestions=suggestions)

    try:
        if profile:
            repo.touch_import_mapping_profile(db, profile=profile)
        for row_item in rows:
            normalized = _apply_header_mapping(row_item.raw_json, mapping)
            repo.update_import_job_row_mapping(db, row=row_item, normalized_json=normalized or None)
        current_raw = job.raw_json if isinstance(job.raw_json, dict) else {}
        repo.update_import_job_mapping_metadata(
            db,
            job=job,
            raw_json={
                **current_raw,
                "mapping": response.model_dump(),
            },
        )
        _save_mapping_profile_if_requested(
            db,
            auth,
            job=job,
            header_signature=header_signature,
            mapping=mapping,
            save_profile=request.save_profile,
            profile_name=request.profile_name,
        )
        db.commit()
        return response.model_dump()
    except Exception:
        db.rollback()
        raise


def apply_import_job_mapping(db: Session, auth: AuthContext, *, job_id: int, request: ImportMappingApplyRequest) -> dict:
    _require_import_manage(auth)
    row = repo.get_import_job(db, job_id)
    if row is None:
        raise _business_error("IMPORT_JOB_NOT_FOUND", "Import job을 찾을 수 없습니다.", 404)
    job, _, _ = row
    _ensure_job_access(auth, job)
    rows = repo.list_import_job_rows_for_validation(db, job_id=job.id)
    if not rows:
        raise _business_error("IMPORT_JOB_MAPPING_NO_ROWS", "매핑할 row가 없습니다.")

    field_names = _canonical_field_names(job.import_type)
    mapping = {str(source).strip(): str(target).strip() for source, target in request.mapping_json.items() if str(source).strip()}
    invalid_targets = sorted({target for target in mapping.values() if target not in field_names})
    if invalid_targets:
        raise _business_error("IMPORT_JOB_MAPPING_TARGET_INVALID", "지원하지 않는 매핑 대상 필드가 있습니다.")

    headers = _collect_headers(rows)
    header_signature = _headers_signature(headers)
    suggestions = [
        {
            "source_header": header,
            "target_field": mapping.get(header),
            "confidence": 1.0 if mapping.get(header) else 0,
            "status": "MANUAL" if mapping.get(header) else "UNMAPPED",
        }
        for header in headers
    ]
    response = _mapping_response_from_job(db, job=job, rows=rows, mapping=mapping, suggestions=suggestions)

    try:
        for row_item in rows:
            normalized = _apply_header_mapping(row_item.raw_json, mapping)
            repo.update_import_job_row_mapping(db, row=row_item, normalized_json=normalized or None)
        current_raw = job.raw_json if isinstance(job.raw_json, dict) else {}
        repo.update_import_job_mapping_metadata(
            db,
            job=job,
            raw_json={
                **current_raw,
                "mapping": response.model_dump(),
            },
        )
        _save_mapping_profile_if_requested(
            db,
            auth,
            job=job,
            header_signature=header_signature,
            mapping=mapping,
            save_profile=request.save_profile,
            profile_name=request.profile_name,
        )
        db.commit()
        return response.model_dump()
    except Exception:
        db.rollback()
        raise


def list_mapping_profiles(
    db: Session,
    auth: AuthContext,
    *,
    client_id: int | None = None,
    import_type: str | None = None,
    source_type: str | None = None,
) -> dict:
    _require_import_view(auth)
    effective_client_id = resolve_effective_client_id(auth, client_id, allow_all_clients=True)
    items = repo.list_import_mapping_profiles(
        db,
        client_id=effective_client_id,
        import_type=import_type,
        source_type=source_type,
        active_only=True,
    )
    return ImportMappingProfilesResponse(items=[_profile_response(item) for item in items]).model_dump()


def create_mapping_profile(db: Session, auth: AuthContext, request: ImportMappingProfileCreateRequest) -> dict:
    _require_import_manage(auth)
    client_id = resolve_effective_client_id(auth, request.client_id, allow_all_clients=True)
    safe_import_type = _ensure_import_type(request.import_type)
    safe_source_type = _ensure_source_type(request.source_type)
    profile = repo.create_or_update_import_mapping_profile(
        db,
        client_id=client_id,
        import_type=safe_import_type,
        source_type=safe_source_type,
        profile_name=request.profile_name,
        header_signature=request.header_signature,
        mapping_json=request.mapping_json,
        created_by=auth.user_id,
    )
    db.commit()
    return _profile_response(profile).model_dump()


def build_import_template(db: Session, auth: AuthContext, import_type: str) -> tuple[str, bytes]:
    _require_import_view(auth)
    safe_import_type = _ensure_import_type(import_type)
    if safe_import_type != "PRODUCT_MASTER":
        raise _business_error("IMPORT_TEMPLATE_UNSUPPORTED", "현재는 PRODUCT_MASTER 양식만 제공합니다.")
    headers = [
        "고객사명",
        "상품코드",
        "상품명",
        "옵션명",
        "대표바코드",
        "추가바코드",
        "카톤바코드",
        "카톤입수",
        "사용여부",
        "메모",
    ]
    csv_text = "\ufeff" + ",".join(headers) + "\r\n"
    return "product-master-template.csv", csv_text.encode("utf-8")


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


def _first_text_value(data: dict, *field_names: str) -> str | None:
    for field_name in field_names:
        value = _text_value(data, field_name)
        if value:
            return value
    return None


def _bool_value_or_default(data: dict, field_name: str, default: bool) -> bool:
    value = data.get(field_name)
    if _is_blank(value):
        return default
    text = str(value).strip().lower()
    if text in {"y", "yes", "true", "1", "사용", "사용중", "활성", "active"}:
        return True
    if text in {"n", "no", "false", "0", "미사용", "사용중지", "비활성", "inactive"}:
        return False
    return default


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


def _safe_find_product_by_code(db: Session, client_id: int, product_code: str):
    if not inspect(db.get_bind()).has_table("products"):
        return None
    return master_repository.find_product_by_code(db, client_id, product_code)


def _safe_find_product_by_barcode(db: Session, client_id: int, barcode: str):
    if not inspect(db.get_bind()).has_table("products"):
        return None
    return master_repository.find_product_by_barcode(db, client_id, barcode)


def _safe_find_product_barcode_by_norm(db: Session, client_id: int, barcode: str):
    if not inspect(db.get_bind()).has_table("product_barcodes"):
        return None
    return master_repository.find_product_barcode_by_norm(db, client_id, barcode)


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


def _validate_product_master(db: Session, client_id: int, data: dict, seen: dict[str, set[str]]) -> list[dict]:
    issues = []
    issues.extend(_required_field(data, "product_code"))
    issues.extend(_required_field(data, "product_name"))
    product_code = _text_value(data, "product_code")
    if product_code:
        if product_code in seen.setdefault("product_code", set()):
            issues.append(
                _issue(
                    field_name="product_code",
                    raw_value=product_code,
                    error_code="PRODUCT_CODE_DUPLICATED_IN_JOB",
                    error_message="같은 업로드 자료 안에 중복 상품코드가 있습니다.",
                )
            )
        seen["product_code"].add(product_code)

    primary_barcode = _first_text_value(data, "primary_barcode", "barcode")
    if not primary_barcode:
        issues.append(
            _issue(
                field_name="primary_barcode",
                raw_value=data.get("primary_barcode") or data.get("barcode"),
                error_code="PRODUCT_BARCODE_MISSING",
                error_message="대표바코드가 비어 있습니다.",
                severity="WARNING",
            )
        )
    for field_name in ("primary_barcode", "additional_barcode", "carton_barcode"):
        barcode = _text_value(data, field_name)
        if not barcode:
            continue
        if barcode in seen.setdefault("barcode", set()):
            issues.append(
                _issue(
                    field_name=field_name,
                    raw_value=barcode,
                    error_code="BARCODE_DUPLICATED_IN_JOB",
                    error_message="같은 업로드 자료 안에 중복 바코드가 있습니다.",
                )
            )
        seen["barcode"].add(barcode)
        existing_product = _safe_find_product_by_barcode(db, client_id, barcode)
        existing_barcode = _safe_find_product_barcode_by_norm(db, client_id, barcode)
        if product_code and existing_product and existing_product.product_code != product_code:
            issues.append(
                _issue(
                    field_name=field_name,
                    raw_value=barcode,
                    error_code="BARCODE_BELONGS_TO_ANOTHER_PRODUCT",
                    error_message="바코드가 같은 고객사의 다른 상품에 이미 연결되어 있습니다.",
                )
            )
        if product_code and existing_barcode:
            barcode_product = master_repository.get_product_by_id(db, existing_barcode.product_id)
            if barcode_product and barcode_product.product_code != product_code:
                issues.append(
                    _issue(
                        field_name=field_name,
                        raw_value=barcode,
                        error_code="BARCODE_BELONGS_TO_ANOTHER_PRODUCT",
                        error_message="바코드가 같은 고객사의 다른 상품에 이미 연결되어 있습니다.",
                    )
                )
    issues.extend(_number_min_if_present(data, "unit_qty", min_value=1))
    if product_code and _safe_find_product_by_code(db, client_id, product_code):
        issues.append(
            _issue(
                field_name="product_code",
                raw_value=product_code,
                error_code="PRODUCT_ALREADY_EXISTS_UPDATE_REVIEW",
                error_message="이미 존재하는 상품코드입니다. 확정 시 수정 후보로 처리됩니다.",
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


def _validate_import_row(db: Session, *, import_type: str, client_id: int | None, data: dict, seen: dict[str, set[str]]) -> list[dict]:
    if import_type == "PRODUCT_MASTER":
        if client_id is None:
            return [
                _issue(
                    field_name="client_id",
                    raw_value=None,
                    error_code="IMPORT_JOB_REQUESTED_CLIENT_REQUIRED",
                    error_message="상품 마스터 import에는 고객사가 필요합니다.",
                )
            ]
        return _validate_product_master(db, client_id, data, seen)
    validators = {
        "PRODUCT_BARCODE": _validate_product_barcode,
        "RETURN_RECEPTION": _validate_return_reception,
        "RETURN_INTAKE": _validate_return_reception,
        "RETURN_EXPECTED": _validate_return_expected,
        "INBOUND_EXPECTED": _validate_inbound_expected,
        "OUTBOUND_ORDER": _validate_outbound_order,
    }
    validator = validators.get(import_type)
    if validator is None:
        return [
            _issue(
                field_name="import_type",
                raw_value=import_type,
                error_code="IMPORT_TYPE_CONFIRM_HANDLER_NOT_READY",
                error_message="이 import_type은 필드 skeleton만 준비되었고 저장 handler는 후속 구현 대상입니다.",
            )
        ]
    return validator(data)


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

    normalized_rows = _normalize_paste_rows(request)
    filtered = _filter_actual_import_rows(job.import_type, normalized_rows)
    rows = filtered.rows
    if not rows:
        raise _business_error("IMPORT_JOB_NO_DATA_ROWS", "실제 데이터 행이 없습니다.")
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
        updated_job.raw_json = {
            **(updated_job.raw_json if isinstance(updated_job.raw_json, dict) else {}),
            "row_filter": _row_filter_summary(filtered),
        }
        db.flush()
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
            skipped_empty_rows=filtered.skipped_empty_rows,
            skipped_noise_rows=filtered.skipped_noise_rows,
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
    parsed = _parse_xlsx_rows(file_bytes, job.import_type)

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
        updated_job.raw_json = {
            "headers": parsed.headers,
            "mapped_headers": parsed.mapped_headers,
            "unmapped_headers": parsed.unmapped_headers,
            "worksheet_name": parsed.worksheet_name,
            "row_filter": {
                "skipped_empty_rows": parsed.skipped_empty_rows,
                "skipped_noise_rows": parsed.skipped_noise_rows,
            },
        }
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
            mapped_headers=parsed.mapped_headers,
            unmapped_headers=parsed.unmapped_headers,
            skipped_empty_rows=parsed.skipped_empty_rows,
            skipped_noise_rows=parsed.skipped_noise_rows,
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
        seen_values: dict[str, set[str]] = {}
        row_statuses: list[tuple[int, str, str | None]] = []

        for row_item in rows:
            issues = _validate_import_row(
                db,
                import_type=job.import_type,
                client_id=job.requested_client_id,
                data=_row_data(row_item),
                seen=seen_values,
            )
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
            row_statuses.append((row_item.id, status, _validation_message(issues)))
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
        repo.force_import_job_row_validation_statuses(db, statuses=row_statuses)
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
    primary_barcode = _first_text_value(data, "primary_barcode", "barcode")
    additional_barcode = _text_value(data, "additional_barcode")
    carton_barcode = _text_value(data, "carton_barcode")
    option_name = _text_value(data, "option_name")
    memo = _text_value(data, "memo")
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
            specification=option_name,
            remarks=memo,
        )
        product.active_yn = _bool_value_or_default(data, "is_active", True)
        created_product = True

    created_barcode_count = 0
    if primary_barcode and not _barcode_exists(db, client_id=client_id, barcode=primary_barcode):
        created_barcode, _barcode_id = _create_barcode_if_missing(
            db,
            client_id=client_id,
            product_id=product.id,
            barcode=primary_barcode,
            barcode_type=DEFAULT_IMPORT_BARCODE_TYPE,
            unit_qty=1,
        )
        created_barcode_count += 1 if created_barcode else 0
    if primary_barcode and not product.barcode:
        product.barcode = primary_barcode

    if additional_barcode:
        created_barcode, _barcode_id = _create_barcode_if_missing(
            db,
            client_id=client_id,
            product_id=product.id,
            barcode=additional_barcode,
            barcode_type="ADDITIONAL",
            unit_qty=1,
        )
        created_barcode_count += 1 if created_barcode else 0

    if carton_barcode:
        unit_qty = _int_value_or_default(data, "unit_qty", 1)
        created_barcode, _barcode_id = _create_barcode_if_missing(
            db,
            client_id=client_id,
            product_id=product.id,
            barcode=carton_barcode,
            barcode_type="CARTON",
            unit_qty=unit_qty,
        )
        created_barcode_count += 1 if created_barcode else 0

    if created_product or created_barcode_count > 0:
        db.flush()
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
