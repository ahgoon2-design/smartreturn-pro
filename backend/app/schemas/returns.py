from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ReturnIntakeBatchCreateRequest(BaseModel):
    client_id: int
    source_type: str = "PASTE"
    source_name: str | None = None
    memo: str | None = None

    @field_validator("source_type")
    @classmethod
    def _required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("required")
        return value

    @field_validator("source_name", "memo")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ReturnIntakePasteRowItem(BaseModel):
    row_no: int | None = None
    order_no: str | None = None
    return_tracking_no: str | None = None
    original_tracking_no: str | None = None
    product_code: str | None = None
    barcode: str | None = None
    product_name: str | None = None
    option_name: str | None = None
    qty: int | str | None = None
    return_reason: str | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_phone_masked: str | None = None
    raw_data: dict[str, Any] | None = None

    @field_validator(
        "order_no",
        "return_tracking_no",
        "original_tracking_no",
        "product_code",
        "barcode",
        "product_name",
        "option_name",
        "return_reason",
        "customer_name",
        "customer_phone",
        "customer_phone_masked",
    )
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = str(value).strip()
        return value or None


class ReturnIntakePasteRowsRequest(BaseModel):
    rows: list[ReturnIntakePasteRowItem] = Field(min_length=1)
    replace_existing: bool = False


class ReturnIntakeBatchSummaryResponse(BaseModel):
    batch_id: int
    client_id: int
    client_code: str | None = None
    client_name: str | None = None
    source_type: str
    source_name: str | None = None
    status: str
    total_rows: int
    valid_rows: int
    warning_rows: int
    error_rows: int
    memo: str | None = None
    created_by: int
    created_at: datetime
    updated_at: datetime


class ReturnIntakeBatchDetailResponse(ReturnIntakeBatchSummaryResponse):
    pass


class ReturnIntakeBatchListResponse(BaseModel):
    items: list[ReturnIntakeBatchSummaryResponse]
    page: int
    page_size: int
    total_count: int


class ReturnIntakeRowResponse(BaseModel):
    row_id: int
    batch_id: int
    client_id: int
    row_no: int
    order_no: str | None = None
    return_tracking_no: str | None = None
    original_tracking_no: str | None = None
    product_code: str | None = None
    barcode: str | None = None
    product_name: str | None = None
    option_name: str | None = None
    qty: int | None = None
    return_reason: str | None = None
    customer_name: str | None = None
    customer_phone_masked: str | None = None
    raw_data: dict[str, Any]
    validation_status: str
    validation_message: str | None = None
    status: str
    judgement_status: str | None = None
    judgement_memo: str | None = None
    judged_at: datetime | None = None
    judged_by: int | None = None
    return_management_no: str | None = None
    return_label_no: str | None = None
    label_print_required: bool = False
    label_print_status: str | None = None
    label_printed_at: datetime | None = None
    inventory_reflected_yn: bool = False
    inventory_reflected_at: datetime | None = None
    inventory_event_id: int | None = None
    external_outbound_required: bool = False
    external_outbound_status: str = "NOT_REQUIRED"
    external_outbound_at: datetime | None = None
    external_outbound_confirmed_by: int | None = None
    external_outbound_batch_id: int | None = None
    hold_status: str = "HOLD_PENDING"
    hold_reason: str | None = None
    hold_response_memo: str | None = None
    hold_resolved_at: datetime | None = None
    hold_resolved_by: int | None = None
    disposal_status: str = "DISPOSAL_PENDING"
    disposal_reason: str | None = None
    disposal_memo: str | None = None
    disposal_confirmed_at: datetime | None = None
    disposal_confirmed_by: int | None = None
    created_at: datetime
    updated_at: datetime


class ReturnIntakeRowsResponse(BaseModel):
    items: list[ReturnIntakeRowResponse]
    page: int
    page_size: int
    total_count: int


class ReturnIntakePasteRowsResponse(BaseModel):
    batch_id: int
    saved_row_count: int
    status: str
    total_rows: int
    valid_rows: int
    warning_rows: int
    error_rows: int


class ReturnIntakeValidateResponse(BaseModel):
    batch_id: int
    status: str
    total_rows: int
    valid_rows: int
    warning_rows: int
    error_rows: int


class ReturnIntakePrepareProcessingResponse(BaseModel):
    batch_id: int
    total_rows: int
    prepared_rows: int
    skipped_rows: int
    invalid_rows: int
    warning_rows: int
    status: str
    message: str


class ReturnProcessingTaskResponse(BaseModel):
    task_id: int
    row_id: int
    batch_id: int
    client_id: int
    client_code: str | None = None
    client_name: str | None = None
    row_no: int
    order_no: str | None = None
    return_tracking_no: str | None = None
    original_tracking_no: str | None = None
    product_code: str | None = None
    barcode: str | None = None
    product_name: str | None = None
    option_name: str | None = None
    qty: int | None = None
    return_reason: str | None = None
    validation_status: str
    status: str
    judgement_status: str | None = None
    judgement_memo: str | None = None
    judged_at: datetime | None = None
    judged_by: int | None = None
    return_management_no: str | None = None
    return_label_no: str | None = None
    label_print_required: bool = False
    label_print_status: str | None = None
    label_printed_at: datetime | None = None
    inventory_reflected_yn: bool = False
    inventory_reflected_at: datetime | None = None
    inventory_event_id: int | None = None
    external_outbound_required: bool = False
    external_outbound_status: str = "NOT_REQUIRED"
    external_outbound_at: datetime | None = None
    external_outbound_confirmed_by: int | None = None
    external_outbound_batch_id: int | None = None
    hold_status: str = "HOLD_PENDING"
    hold_reason: str | None = None
    hold_response_memo: str | None = None
    hold_resolved_at: datetime | None = None
    hold_resolved_by: int | None = None
    disposal_status: str = "DISPOSAL_PENDING"
    disposal_reason: str | None = None
    disposal_memo: str | None = None
    disposal_confirmed_at: datetime | None = None
    disposal_confirmed_by: int | None = None
    created_at: datetime
    updated_at: datetime


class ReturnProcessingTaskListResponse(BaseModel):
    items: list[ReturnProcessingTaskResponse]
    page: int
    page_size: int
    total_count: int


class ReturnProcessingJudgeRequest(BaseModel):
    judgement_status: str
    judgement_memo: str | None = None
    print_label: bool | None = None

    @field_validator("judgement_status")
    @classmethod
    def _required_status(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("required")
        return value

    @field_validator("judgement_memo")
    @classmethod
    def _optional_memo(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ReturnProcessingJudgeResponse(ReturnProcessingTaskResponse):
    message: str


class ReturnProcessingAttachmentResponse(BaseModel):
    attachment_id: int
    task_id: int
    row_id: int
    batch_id: int
    client_id: int
    attachment_type: str
    original_filename: str
    content_type: str
    file_size: int
    note: str | None = None
    uploaded_by: int
    uploaded_at: datetime
    active_yn: bool
    preview_url: str | None = None
    download_url: str | None = None


class ReturnProcessingAttachmentListResponse(BaseModel):
    items: list[ReturnProcessingAttachmentResponse]


class ReturnClosingCandidateResponse(BaseModel):
    row_id: int
    task_id: int
    batch_id: int
    client_id: int
    client_code: str | None = None
    client_name: str | None = None
    row_no: int
    order_no: str | None = None
    return_tracking_no: str | None = None
    product_code: str | None = None
    barcode: str | None = None
    product_name: str | None = None
    qty: int | None = None
    judgement_status: str
    return_management_no: str | None = None
    return_label_no: str | None = None
    status: str
    inventory_reflected_yn: bool = False
    inventory_reflected_at: datetime | None = None
    inventory_event_id: int | None = None
    judged_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    closing_action: str
    message: str | None = None


class ReturnClosingCandidateListResponse(BaseModel):
    items: list[ReturnClosingCandidateResponse]
    page: int
    page_size: int
    total_count: int


class ReturnClosingConfirmRequest(BaseModel):
    row_ids: list[int] = Field(min_length=1)
    client_id: int | None = None
    confirm_good_only: bool = True


class ReturnClosingRowResult(BaseModel):
    row_id: int
    judgement_status: str | None = None
    result: str
    message: str
    inventory_event_id: int | None = None


class ReturnClosingConfirmResponse(BaseModel):
    total_rows: int
    reflected_rows: int
    skipped_rows: int
    failed_rows: int
    followup_rows: int
    event_count: int
    message: str
    row_results: list[ReturnClosingRowResult]


class ReturnExternalOutboundCandidateResponse(BaseModel):
    row_id: int
    task_id: int
    batch_id: int
    client_id: int
    client_code: str | None = None
    client_name: str | None = None
    row_no: int
    order_no: str | None = None
    return_tracking_no: str | None = None
    product_code: str | None = None
    barcode: str | None = None
    product_name: str | None = None
    option_name: str | None = None
    qty: int | None = None
    judgement_status: str
    return_management_no: str | None = None
    return_label_no: str | None = None
    external_outbound_required: bool = False
    external_outbound_status: str
    external_outbound_at: datetime | None = None
    external_outbound_confirmed_by: int | None = None
    external_outbound_batch_id: int | None = None
    judged_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ReturnExternalOutboundCandidateListResponse(BaseModel):
    items: list[ReturnExternalOutboundCandidateResponse]
    page: int
    page_size: int
    total_count: int


class ReturnExternalOutboundConfirmRequest(BaseModel):
    row_ids: list[int] = Field(min_length=1)
    scanned_numbers: list[str] | None = None
    client_id: int | None = None


class ReturnExternalOutboundRowResult(BaseModel):
    row_id: int
    judgement_status: str | None = None
    result: str
    message: str
    external_outbound_status: str | None = None
    external_outbound_batch_id: int | None = None


class ReturnExternalOutboundConfirmResponse(BaseModel):
    batch_id: int | None = None
    batch_no: str | None = None
    total_rows: int
    confirmed_rows: int
    skipped_rows: int
    failed_rows: int
    message: str
    row_results: list[ReturnExternalOutboundRowResult]


class ReturnExternalOutboundBatchSummaryResponse(BaseModel):
    batch_id: int
    batch_no: str
    client_id: int | None = None
    client_code: str | None = None
    client_name: str | None = None
    status: str
    target_type: str
    total_rows: int
    confirmed_rows: int
    memo: str | None = None
    created_by: int
    created_at: datetime
    confirmed_by: int | None = None
    confirmed_at: datetime | None = None


class ReturnExternalOutboundBatchListResponse(BaseModel):
    items: list[ReturnExternalOutboundBatchSummaryResponse]
    page: int
    page_size: int
    total_count: int


class ReturnExternalOutboundBatchRowResponse(BaseModel):
    row_id: int
    task_id: int
    batch_id: int
    client_id: int
    client_code: str | None = None
    client_name: str | None = None
    row_no: int
    order_no: str | None = None
    return_tracking_no: str | None = None
    product_code: str | None = None
    barcode: str | None = None
    product_name: str | None = None
    option_name: str | None = None
    qty: int | None = None
    judgement_status: str
    return_management_no: str | None = None
    return_label_no: str | None = None
    external_outbound_status: str
    external_outbound_at: datetime | None = None
    external_outbound_confirmed_by: int | None = None


class ReturnExternalOutboundBatchDetailResponse(ReturnExternalOutboundBatchSummaryResponse):
    rows: list[ReturnExternalOutboundBatchRowResponse]


class ReturnHoldCandidateResponse(BaseModel):
    row_id: int
    task_id: int
    batch_id: int
    client_id: int
    client_code: str | None = None
    client_name: str | None = None
    row_no: int
    order_no: str | None = None
    return_tracking_no: str | None = None
    product_code: str | None = None
    barcode: str | None = None
    product_name: str | None = None
    option_name: str | None = None
    qty: int | None = None
    return_reason: str | None = None
    judgement_status: str
    judgement_memo: str | None = None
    hold_status: str
    hold_reason: str | None = None
    hold_response_memo: str | None = None
    hold_resolved_at: datetime | None = None
    hold_resolved_by: int | None = None
    return_management_no: str | None = None
    return_label_no: str | None = None
    judged_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ReturnHoldCandidateListResponse(BaseModel):
    items: list[ReturnHoldCandidateResponse]
    page: int
    page_size: int
    total_count: int


class ReturnHoldUpdateRequest(BaseModel):
    hold_status: str
    hold_reason: str | None = None
    hold_response_memo: str | None = None

    @field_validator("hold_status")
    @classmethod
    def _required_hold_status(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("required")
        return value

    @field_validator("hold_reason", "hold_response_memo")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ReturnHoldUpdateResponse(ReturnHoldCandidateResponse):
    message: str


class ReturnHoldRejudgeRequest(BaseModel):
    judgement_status: str
    judgement_memo: str | None = None
    hold_response_memo: str | None = None

    @field_validator("judgement_status")
    @classmethod
    def _required_judgement_status(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("required")
        return value

    @field_validator("judgement_memo", "hold_response_memo")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ReturnHoldRejudgeResponse(ReturnProcessingTaskResponse):
    message: str


class ReturnDisposalCandidateResponse(BaseModel):
    row_id: int
    task_id: int
    batch_id: int
    client_id: int
    client_code: str | None = None
    client_name: str | None = None
    row_no: int
    order_no: str | None = None
    return_tracking_no: str | None = None
    product_code: str | None = None
    barcode: str | None = None
    product_name: str | None = None
    option_name: str | None = None
    qty: int | None = None
    return_reason: str | None = None
    judgement_status: str
    judgement_memo: str | None = None
    disposal_status: str
    disposal_reason: str | None = None
    disposal_memo: str | None = None
    disposal_confirmed_at: datetime | None = None
    disposal_confirmed_by: int | None = None
    return_management_no: str | None = None
    return_label_no: str | None = None
    judged_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ReturnDisposalCandidateListResponse(BaseModel):
    items: list[ReturnDisposalCandidateResponse]
    page: int
    page_size: int
    total_count: int


class ReturnDisposalConfirmRequest(BaseModel):
    disposal_reason: str | None = None
    disposal_memo: str | None = None

    @field_validator("disposal_reason", "disposal_memo")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ReturnDisposalConfirmResponse(ReturnDisposalCandidateResponse):
    message: str


class ReturnHistoryItemResponse(BaseModel):
    row_id: int
    task_id: int
    batch_id: int
    client_id: int
    client_code: str | None = None
    client_name: str | None = None
    row_no: int
    order_no: str | None = None
    return_tracking_no: str | None = None
    original_tracking_no: str | None = None
    product_code: str | None = None
    barcode: str | None = None
    product_name: str | None = None
    option_name: str | None = None
    qty: int | None = None
    return_reason: str | None = None
    validation_status: str
    status: str
    judgement_status: str | None = None
    judgement_memo: str | None = None
    return_management_no: str | None = None
    return_label_no: str | None = None
    label_print_required: bool = False
    label_print_status: str | None = None
    label_printed_at: datetime | None = None
    inventory_reflected_yn: bool = False
    inventory_reflected_at: datetime | None = None
    inventory_event_id: int | None = None
    external_outbound_status: str | None = None
    external_outbound_at: datetime | None = None
    external_outbound_batch_id: int | None = None
    hold_status: str | None = None
    hold_reason: str | None = None
    hold_response_memo: str | None = None
    hold_resolved_at: datetime | None = None
    disposal_status: str | None = None
    disposal_reason: str | None = None
    disposal_memo: str | None = None
    disposal_confirmed_at: datetime | None = None
    attachment_count: int = 0
    followup_status: str
    followup_status_label: str
    created_at: datetime
    updated_at: datetime
    judged_at: datetime | None = None


class ReturnHistoryListResponse(BaseModel):
    items: list[ReturnHistoryItemResponse]
    page: int
    page_size: int
    total_count: int
