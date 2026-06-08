from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_auth_context, get_db
from app.core.permissions import require_password_change_completed
from app.schemas.auth import AuthContext
from app.schemas.channels import ChannelAccountCreateRequest, ChannelAccountUpdateRequest, ChannelSyncDryRunRequest
from app.schemas.common import ApiResult, api_success
from app.services.channel_service import account_service, sync_service


router = APIRouter(prefix="/api/channels", tags=["channels"])


def _require_ready(auth: AuthContext) -> None:
    require_password_change_completed(auth)


@router.get("/accounts", response_model=ApiResult)
def list_channel_accounts_api(
    client_id: int | None = None,
    channel_type: str | None = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_ready(auth)
    return api_success(
        result_code="CHANNEL_ACCOUNTS_FOUND",
        message="채널 계정 목록을 조회했습니다.",
        data=account_service.list_accounts(
            db,
            auth,
            client_id=client_id,
            channel_type=channel_type,
            include_inactive=include_inactive,
        ),
    )


@router.post("/accounts", response_model=ApiResult)
def create_channel_account_api(
    request: ChannelAccountCreateRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_ready(auth)
    return api_success(
        result_code="CHANNEL_ACCOUNT_CREATED",
        message="채널 계정을 생성했습니다.",
        data=account_service.create_account(db, auth, request),
    )


@router.get("/accounts/{account_id}", response_model=ApiResult)
def get_channel_account_api(
    account_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_ready(auth)
    return api_success(
        result_code="CHANNEL_ACCOUNT_FOUND",
        message="채널 계정을 조회했습니다.",
        data=account_service.get_account(db, auth, account_id=account_id),
    )


@router.patch("/accounts/{account_id}", response_model=ApiResult)
def update_channel_account_api(
    account_id: int,
    request: ChannelAccountUpdateRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_ready(auth)
    return api_success(
        result_code="CHANNEL_ACCOUNT_UPDATED",
        message="채널 계정을 수정했습니다.",
        data=account_service.update_account(db, auth, account_id=account_id, request=request),
    )


@router.post("/accounts/{account_id}/disable", response_model=ApiResult)
def disable_channel_account_api(
    account_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_ready(auth)
    return api_success(
        result_code="CHANNEL_ACCOUNT_DISABLED",
        message="채널 계정을 비활성화했습니다.",
        data=account_service.disable_account(db, auth, account_id=account_id),
    )


@router.post("/accounts/{account_id}/test-connection", response_model=ApiResult)
def test_channel_connection_api(
    account_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_ready(auth)
    return api_success(
        result_code="CHANNEL_ACCOUNT_CONNECTION_TESTED",
        message="채널 계정 dry-run 연결 테스트를 실행했습니다.",
        data=account_service.test_connection_dry_run(db, auth, account_id=account_id),
    )


@router.get("/accounts/{account_id}/sync-jobs", response_model=ApiResult)
def list_channel_account_sync_jobs_api(
    account_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_ready(auth)
    return api_success(
        result_code="CHANNEL_SYNC_JOBS_FOUND",
        message="채널 수집 job 목록을 조회했습니다.",
        data=sync_service.list_sync_jobs(db, auth, account_id=account_id),
    )


@router.post("/accounts/{account_id}/sync-jobs/dry-run", response_model=ApiResult)
def create_channel_dry_run_sync_job_api(
    account_id: int,
    request: ChannelSyncDryRunRequest | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_ready(auth)
    return api_success(
        result_code="CHANNEL_SYNC_DRY_RUN_CREATED",
        message="채널 dry-run 수집 job을 생성했습니다.",
        data=sync_service.start_dry_run_job(db, auth, account_id=account_id, request=request or ChannelSyncDryRunRequest()),
    )


@router.get("/raw-events", response_model=ApiResult)
def list_channel_raw_events_api(
    account_id: int | None = None,
    process_status: str | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_ready(auth)
    return api_success(
        result_code="CHANNEL_RAW_EVENTS_FOUND",
        message="채널 원본 이벤트 목록을 조회했습니다.",
        data=sync_service.list_raw_events(db, auth, account_id=account_id, process_status=process_status),
    )


@router.get("/raw-events/{event_id}", response_model=ApiResult)
def get_channel_raw_event_api(
    event_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_ready(auth)
    return api_success(
        result_code="CHANNEL_RAW_EVENT_FOUND",
        message="채널 원본 이벤트를 조회했습니다.",
        data=sync_service.get_raw_event(db, auth, event_id=event_id),
    )


@router.get("/sync-jobs", response_model=ApiResult)
def list_channel_sync_jobs_api(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_ready(auth)
    return api_success(
        result_code="CHANNEL_SYNC_JOBS_FOUND",
        message="채널 수집 job 목록을 조회했습니다.",
        data=sync_service.list_sync_jobs(db, auth),
    )
