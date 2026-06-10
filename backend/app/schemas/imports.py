"""Import job API schema."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ImportJobCreateRequest(BaseModel):
    import_type: str
    source_type: str
    source_name: str | None = None
    requested_client_id: int | None = None
    requested_warehouse_id: int | None = None
    file_name: str | None = None
    worksheet_name: str | None = None
    message: str | None = None
    raw_json: dict | None = None

    @field_validator("import_type", "source_type")
    @classmethod
    def _required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("required")
        return value

    @field_validator("source_name", "file_name", "worksheet_name", "message")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ImportPasteRowItem(BaseModel):
    row_no: int | None = None
    raw_json: dict
    normalized_json: dict | None = None
    source_row_key: str | None = None

    @field_validator("source_row_key")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ImportPasteRowsRequest(BaseModel):
    rows: list[ImportPasteRowItem]
    replace_existing: bool = False
    source_name: str | None = None
    worksheet_name: str | None = None

    @field_validator("source_name", "worksheet_name")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ImportPasteRowsResponse(BaseModel):
    job_id: int
    saved_row_count: int
    status: str
    total_rows: int
    parsed_rows: int
    valid_rows: int
    invalid_rows: int
    error_rows: int
    progress_percent: int
    skipped_empty_rows: int = 0
    skipped_noise_rows: int = 0
    skipped_rows_total: int = 0
    total_read_rows: int = 0


class ImportExcelUploadResponse(BaseModel):
    job_id: int
    saved_row_count: int
    status: str
    total_rows: int
    parsed_rows: int
    valid_rows: int
    invalid_rows: int
    error_rows: int
    progress_percent: int
    file_name: str
    worksheet_name: str
    header_row_no: int = 1
    total_read_rows: int = 0
    headers: list[str]
    mapped_headers: dict[str, str] = Field(default_factory=dict)
    unmapped_headers: list[str] = Field(default_factory=list)
    skipped_empty_rows: int = 0
    skipped_noise_rows: int = 0
    skipped_rows_total: int = 0


class ImportValidationRunRequest(BaseModel):
    force: bool = False


class ImportCanonicalFieldResponse(BaseModel):
    field_name: str
    label: str
    required: bool = False
    aliases: list[str] = Field(default_factory=list)


class ImportSourceTypeResponse(BaseModel):
    import_types: list[str]
    source_types: list[str]


class ImportMappingSuggestionItem(BaseModel):
    source_header: str
    target_field: str | None = None
    confidence: float = 0
    status: str
    canonical_field: str | None = None
    decision_level: str | None = None
    reason: str | None = None
    provider: str | None = None
    providers: list[str] = Field(default_factory=list)
    is_required: bool = False
    is_risky_field: bool = False
    previous_profile_matched: bool = False
    decision_history_count: int = 0
    conflict_reason: str | None = None
    alternative_candidates: list[dict] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    blocked_reason: str | None = None
    user_action_required: bool = False
    needs_user_confirmation: bool = False
    is_auto_applied: bool = False


class ImportAutoMapRequest(BaseModel):
    save_profile: bool = False
    profile_name: str | None = None


class ImportMappingApplyRequest(BaseModel):
    mapping_json: dict[str, str]
    save_profile: bool = False
    profile_name: str | None = None

    @field_validator("profile_name")
    @classmethod
    def _optional_profile_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ImportMappingResponse(BaseModel):
    job_id: int
    import_type: str
    source_type: str
    header_signature: str
    applied_mapping: dict[str, str]
    suggestions: list[ImportMappingSuggestionItem]
    mapped_rows: int
    confirmation_required: bool
    low_confidence_headers: list[str] = Field(default_factory=list)
    ambiguous_headers: list[str] = Field(default_factory=list)
    unmapped_headers: list[str] = Field(default_factory=list)
    required_missing_fields: list[str] = Field(default_factory=list)
    decision_summary: dict = Field(default_factory=dict)
    blocked_reasons: list[str] = Field(default_factory=list)
    confirm_block_reasons: list[str] = Field(default_factory=list)
    can_confirm: bool = False
    required_fields_status: dict = Field(default_factory=dict)
    auto_apply_count: int = 0
    needs_review_count: int = 0
    low_confidence_count: int = 0
    blocked_count: int = 0
    profile_match_status: str | None = None
    learning_status: str | None = None


class ImportMappingProfileCreateRequest(BaseModel):
    client_id: int | None = None
    import_type: str
    source_type: str
    profile_name: str
    header_signature: str
    mapping_json: dict[str, str]

    @field_validator("import_type", "source_type", "profile_name", "header_signature")
    @classmethod
    def _required_profile_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("required")
        return value


class ImportMappingProfileResponse(BaseModel):
    profile_id: int
    client_id: int | None = None
    import_type: str
    source_type: str
    profile_name: str
    header_signature: str
    mapping_json: dict[str, str]
    active_yn: bool
    last_used_at: datetime | None = None
    created_by: int
    created_at: datetime
    updated_at: datetime


class ImportMappingProfilesResponse(BaseModel):
    items: list[ImportMappingProfileResponse]


class ImportValidationRunResponse(BaseModel):
    job_id: int
    status: str
    total_rows: int
    validated_row_count: int
    valid_rows: int
    invalid_rows: int
    warning_rows: int
    error_rows: int
    validation_error_count: int
    progress_percent: int


class ImportConfirmResponse(BaseModel):
    job_id: int
    import_type: str
    source_type: str
    status: str
    total_rows: int
    applied_rows: int
    skipped_rows: int
    failed_rows: int
    warning_rows: int
    invalid_rows: int
    result_code: str
    message: str


class ImportPageMeta(BaseModel):
    page: int
    page_size: int
    total_count: int


class ImportJobFileResponse(BaseModel):
    file_id: int
    file_name: str
    stored_file_name: str | None = None
    relative_path: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    uploaded_by: int
    uploaded_at: datetime


class ImportJobSummaryResponse(BaseModel):
    job_id: int
    import_type: str
    source_type: str
    source_name: str | None = None
    requested_client_id: int | None = None
    requested_client_name: str | None = None
    requested_warehouse_id: int | None = None
    requested_warehouse_name: str | None = None
    status: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    error_rows: int
    progress_percent: int
    total_read_rows: int = 0
    skipped_empty_rows: int = 0
    skipped_noise_rows: int = 0
    skipped_rows_total: int = 0
    header_row_no: int | None = None
    file_name: str | None = None
    worksheet_name: str | None = None
    created_by: int
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime


class ImportJobDetailResponse(ImportJobSummaryResponse):
    parsed_rows: int
    inserted_rows: int
    updated_rows: int
    skipped_rows: int
    message: str | None = None
    raw_json: dict | None = None
    files: list[ImportJobFileResponse] = Field(default_factory=list)


class ImportJobRowResponse(BaseModel):
    row_id: int
    job_id: int
    client_id: int | None = None
    row_no: int
    source_row_key: str | None = None
    row_hash: str | None = None
    raw_json: dict
    normalized_json: dict | None = None
    validation_status: str
    validation_message: str | None = None
    target_action: str | None = None
    target_table: str | None = None
    target_id: int | None = None
    created_at: datetime
    updated_at: datetime


class ImportValidationErrorResponse(BaseModel):
    error_id: int
    job_id: int
    row_id: int | None = None
    row_no: int | None = None
    field_name: str | None = None
    raw_value: str | None = None
    error_code: str
    error_message: str
    severity: str
    created_at: datetime


class ImportJobListResponse(BaseModel):
    items: list[ImportJobSummaryResponse]
    page: int
    page_size: int
    total_count: int


class ImportJobRowsResponse(BaseModel):
    items: list[ImportJobRowResponse]
    page: int
    page_size: int
    total_count: int


class ImportJobErrorsResponse(BaseModel):
    items: list[ImportValidationErrorResponse]
    page: int
    page_size: int
    total_count: int
