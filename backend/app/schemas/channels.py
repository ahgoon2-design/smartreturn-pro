from datetime import datetime

from pydantic import BaseModel, Field, field_validator


CHANNEL_TYPES = {"NAVER_SMARTSTORE", "COUPANG", "CAFE24", "EASYADMIN", "COURIER"}
CHANNEL_ACCOUNT_STATUSES = {"ACTIVE", "INACTIVE", "AUTH_REQUIRED", "ERROR"}
CHANNEL_AUTH_STATUSES = {"NOT_CONNECTED", "CONNECTED", "EXPIRED", "ERROR"}
CHANNEL_SYNC_JOB_TYPES = {"COLLECT_CHANGED_ORDERS", "COLLECT_RETURN_CLAIMS", "DRY_RUN"}


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
