from datetime import datetime

from pydantic import BaseModel, Field, field_validator


CHANNEL_TYPES = {"NAVER_SMARTSTORE", "COUPANG", "CAFE24", "EASYADMIN", "COURIER"}
CHANNEL_ACCOUNT_STATUSES = {"ACTIVE", "INACTIVE", "AUTH_REQUIRED", "ERROR"}
CHANNEL_AUTH_STATUSES = {"NOT_CONNECTED", "CONNECTED", "EXPIRED", "ERROR"}
CHANNEL_SYNC_JOB_TYPES = {"COLLECT_CHANGED_ORDERS", "COLLECT_RETURN_CLAIMS", "DRY_RUN"}
CHANNEL_RETURN_CANDIDATE_STATUSES = {
    "READY_FOR_INTAKE",
    "TEAM_ASSIGN_PENDING",
    "PRODUCT_MATCH_PENDING",
    "RETURN_TRACKING_PENDING",
    "NEEDS_REVIEW",
    "BLOCKED",
}
CHANNEL_RETURN_EXPECTED_CREATE_STATUSES = {"NOT_CREATED", "CREATED", "SKIPPED_DUPLICATE", "FAILED"}
CHANNEL_RETURN_CORRECTION_STATUSES = {"NONE", "CORRECTED", "REVIEWED", "REPROCESS_REQUIRED"}
CHANNEL_RETURN_NEXT_ACTIONS = {
    "ASSIGN_TEAM",
    "MATCH_PRODUCT",
    "ENTER_RETURN_TRACKING",
    "REVIEW_CONFLICT",
    "CREATE_RETURN_EXPECTED",
    "ALREADY_CREATED",
    "BLOCKED_NO_ACTION",
}
PRODUCT_CHANNEL_MAPPING_STATUSES = {"ACTIVE", "INACTIVE", "CONFLICT", "REJECTED"}
PRODUCT_CHANNEL_MAPPING_NEXT_ACTIONS = {"APPROVE", "RESOLVE_CONFLICT", "DISABLE", "NO_ACTION"}


class ChannelAccountCreateRequest(BaseModel):
    client_id: int
    client_unit_id: int | None = None
    channel_type: str = "NAVER_SMARTSTORE"
    account_name: str
    store_name: str
    external_account_id: str | None = None
    credential_ref: str | None = None
    sync_enabled: bool = False

    @field_validator("channel_type")
    @classmethod
    def _valid_channel_type(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in CHANNEL_TYPES:
            raise ValueError("unsupported channel_type")
        return value

    @field_validator("account_name", "store_name")
    @classmethod
    def _required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("required")
        return value

    @field_validator("credential_ref")
    @classmethod
    def _optional_credential_ref(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ChannelAccountUpdateRequest(BaseModel):
    client_unit_id: int | None = None
    account_name: str | None = None
    store_name: str | None = None
    external_account_id: str | None = None
    status: str | None = None
    auth_status: str | None = None
    credential_ref: str | None = None
    sync_enabled: bool | None = None

    @field_validator("status")
    @classmethod
    def _valid_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().upper()
        if value not in CHANNEL_ACCOUNT_STATUSES:
            raise ValueError("unsupported status")
        return value

    @field_validator("auth_status")
    @classmethod
    def _valid_auth_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().upper()
        if value not in CHANNEL_AUTH_STATUSES:
            raise ValueError("unsupported auth_status")
        return value

    @field_validator("account_name", "store_name", "external_account_id", "credential_ref")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ChannelAccountResponse(BaseModel):
    id: int
    client_id: int
    client_unit_id: int | None = None
    channel_type: str
    account_name: str
    store_name: str
    external_account_id: str | None = None
    status: str
    auth_status: str
    credential_ref_masked: str | None = None
    last_sync_at: datetime | None = None
    last_success_sync_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    sync_enabled: bool
    created_by: int | None = None
    updated_by: int | None = None
    created_at: datetime
    updated_at: datetime


class ChannelAccountsResponse(BaseModel):
    items: list[ChannelAccountResponse]


class ChannelConnectionTestResponse(BaseModel):
    channel_account_id: int
    channel_type: str
    dry_run: bool = True
    success: bool
    status: str
    auth_status: str
    message: str
    provider_name: str


class ChannelSyncDryRunRequest(BaseModel):
    job_type: str = "DRY_RUN"
    save_mock_event: bool = True

    @field_validator("job_type")
    @classmethod
    def _valid_job_type(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in CHANNEL_SYNC_JOB_TYPES:
            raise ValueError("unsupported job_type")
        return value


class ChannelSyncJobResponse(BaseModel):
    id: int
    channel_account_id: int
    job_type: str
    status: str
    cursor_from: str | None = None
    cursor_to: str | None = None
    cursor_more_from: str | None = None
    cursor_more_sequence: str | None = None
    total_collected: int = 0
    total_inserted: int = 0
    total_updated: int = 0
    total_skipped: int = 0
    total_failed: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime


class ChannelSyncJobsResponse(BaseModel):
    items: list[ChannelSyncJobResponse]


class ChannelSyncDryRunResponse(BaseModel):
    job: ChannelSyncJobResponse
    dry_run: bool = True
    provider_name: str
    collected_event_count: int
    inserted_event_count: int
    updated_event_count: int
    skipped_event_count: int
    message: str


class ChannelRawEventListItem(BaseModel):
    id: int
    channel_account_id: int
    channel_type: str
    event_type: str
    external_order_id: str | None = None
    external_product_order_id: str | None = None
    external_claim_id: str | None = None
    external_tracking_no_hash: str | None = None
    last_changed_at: datetime | None = None
    raw_hash: str
    process_status: str
    process_error_code: str | None = None
    process_error_message: str | None = None
    collected_at: datetime
    created_at: datetime


class ChannelRawEventDetailResponse(ChannelRawEventListItem):
    raw_json: dict = Field(default_factory=dict)


class ChannelRawEventsResponse(BaseModel):
    items: list[ChannelRawEventListItem]


class ChannelReturnCandidateResponse(BaseModel):
    id: int
    channel_raw_event_id: int
    channel_account_id: int
    client_id: int
    client_unit_id: int | None = None
    source_type: str
    source_origin: str
    external_order_id: str | None = None
    external_product_order_id: str | None = None
    external_claim_id: str | None = None
    return_tracking_no: str | None = None
    original_tracking_no: str | None = None
    tracking_no_for_scan: str | None = None
    product_code: str | None = None
    barcode: str | None = None
    product_id: int | None = None
    product_name: str | None = None
    option_name: str | None = None
    qty: int | None = None
    claim_reason: str | None = None
    claim_status: str | None = None
    match_status: str
    match_reason: str
    risk_flags: list[str] = Field(default_factory=list)
    reviewed_at: datetime | None = None
    reviewed_by: int | None = None
    manual_client_unit_id: int | None = None
    manual_product_id: int | None = None
    manual_product_code: str | None = None
    manual_return_tracking_no: str | None = None
    manual_original_tracking_no: str | None = None
    manual_qty: int | None = None
    manual_review_note: str | None = None
    manual_reviewed_by: int | None = None
    manual_reviewed_at: datetime | None = None
    correction_status: str = "NONE"
    correction_summary: dict = Field(default_factory=dict)
    return_expected_id: int | None = None
    return_expected_created_at: datetime | None = None
    return_expected_create_status: str = "NOT_CREATED"
    return_expected_create_error: str | None = None
    action_required: bool = False
    action_reason: str | None = None
    next_recommended_action: str | None = None
    safe_to_create_return_expected: bool = False
    safe_to_reprocess: bool = False
    safe_to_correct: bool = False
    product_mapping_status: str = "NONE"
    product_mapping_id: int | None = None
    product_mapping_conflict_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class ChannelReturnCandidateDetailResponse(ChannelReturnCandidateResponse):
    canonical_json: dict = Field(default_factory=dict)


class ChannelReturnCandidatesResponse(BaseModel):
    items: list[ChannelReturnCandidateResponse]
    summary: dict[str, int] = Field(default_factory=dict)


class ChannelRawEventTransformResponse(BaseModel):
    candidate: ChannelReturnCandidateResponse
    created: bool
    message: str


class ChannelRawEventsBulkTransformResponse(BaseModel):
    transformed_count: int
    created_count: int
    updated_count: int
    failed_count: int
    candidates: list[ChannelReturnCandidateResponse]
    summary: dict[str, int] = Field(default_factory=dict)


class ChannelReturnCandidateActionResponse(BaseModel):
    candidate: ChannelReturnCandidateResponse
    message: str


class ChannelReturnCandidateCorrectionRequest(BaseModel):
    client_unit_id: int | None = None
    product_id: int | None = None
    product_code: str | None = None
    return_tracking_no: str | None = None
    original_tracking_no: str | None = None
    qty: int | None = None
    review_note: str | None = None

    @field_validator("product_code", "return_tracking_no", "original_tracking_no", "review_note")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ChannelReturnExpectedCreateResponse(BaseModel):
    candidate: ChannelReturnCandidateResponse
    return_expected_id: int | None = None
    created: bool = False
    skipped_duplicate: bool = False
    message: str


class ChannelReturnExpectedBulkCreateResponse(BaseModel):
    total_requested: int
    created_count: int
    skipped_duplicate_count: int
    blocked_count: int
    failed_count: int
    created_candidate_ids: list[int] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    error_summary: list[str] = Field(default_factory=list)
    candidates: list[ChannelReturnCandidateResponse] = Field(default_factory=list)


class ChannelDashboardSummaryResponse(BaseModel):
    total_accounts: int = 0
    active_accounts: int = 0
    auth_required_accounts: int = 0
    error_accounts: int = 0
    total_raw_events: int = 0
    raw_events_today: int = 0
    raw_event_failed_count: int = 0
    total_candidates: int = 0
    candidates_today: int = 0
    ready_for_intake_count: int = 0
    team_assign_pending_count: int = 0
    product_match_pending_count: int = 0
    return_tracking_pending_count: int = 0
    needs_review_count: int = 0
    blocked_count: int = 0
    return_expected_created_count: int = 0
    return_expected_failed_count: int = 0
    correction_required_count: int = 0
    corrected_count: int = 0
    product_mapping_count: int = 0
    product_mapping_conflict_count: int = 0
    last_sync_at: datetime | None = None
    last_success_sync_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error_message_summary: str | None = None


class ProductChannelMappingResponse(BaseModel):
    mapping_id: int
    client_id: int
    client_unit_id: int | None = None
    channel_type: str
    channel_account_id: int | None = None
    account_name: str | None = None
    external_seller_product_code: str | None = None
    external_product_name_norm: str | None = None
    external_option_name_norm: str | None = None
    product_id: int
    product_code: str
    product_name: str | None = None
    status: str = "ACTIVE"
    decision_type: str
    confidence: int
    conflict_group_key: str | None = None
    conflict_status: str
    conflict_reason: str | None = None
    approved_by: int | None = None
    approved_at: datetime | None = None
    rejected_by: int | None = None
    rejected_at: datetime | None = None
    disabled_by: int | None = None
    disabled_at: datetime | None = None
    note: str | None = None
    last_used_at: datetime | None = None
    used_count: int = 0
    created_from_candidate_id: int | None = None
    created_at: datetime
    updated_at: datetime
    next_recommended_action: str = "NO_ACTION"


class ProductChannelMappingsResponse(BaseModel):
    items: list[ProductChannelMappingResponse]
    summary: dict[str, int] = Field(default_factory=dict)


class ProductChannelMappingActionRequest(BaseModel):
    note: str | None = None

    @field_validator("note")
    @classmethod
    def _optional_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value[:500] or None


class ProductChannelMappingActionResponse(BaseModel):
    mapping: ProductChannelMappingResponse
    message: str


class ProductChannelMappingConflictRebuildResponse(BaseModel):
    total_count: int
    conflict_count: int
    active_count: int
    updated_count: int
    items: list[ProductChannelMappingResponse] = Field(default_factory=list)
