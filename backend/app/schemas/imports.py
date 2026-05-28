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
