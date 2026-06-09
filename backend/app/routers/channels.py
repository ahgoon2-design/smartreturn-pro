from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_auth_context, get_db
from app.core.permissions import require_password_change_completed
from app.schemas.auth import AuthContext
from app.schemas.channels import (
    ChannelAccountCreateRequest,
    ChannelAccountUpdateRequest,
    ChannelReturnCandidateCorrectionRequest,
    ChannelSyncDryRunRequest,
)
from app.schemas.common import ApiResult, api_success
from app.services.channel_service import account_service, sync_service, transform_service


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


@router.get("/dashboard/summary", response_model=ApiResult)
def get_channel_dashboard_summary_api(
    client_id: int | None = None,
    client_unit_id: int | None = None,
    channel_type: str | None = None,
    account_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_ready(auth)
    return api_success(
        result_code="CHANNEL_DASHBOARD_SUMMARY_FOUND",
        message="채널 자동수집 운영 요약을 조회했습니다.",
        data=transform_service.dashboard_summary(
            db,
            auth,
            client_id=client_id,
            client_unit_id=client_unit_id,
            channel_type=channel_type,
            account_id=account_id,
            date_from=date_from,
            date_to=date_to,
            status=status,
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


@router.post("/raw-events/{event_id}/transform", response_model=ApiResult)
def transform_channel_raw_event_api(
    event_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_ready(auth)
    return api_success(
        result_code="CHANNEL_RAW_EVENT_TRANSFORMED",
        message="채널 원본 이벤트를 반품접수 후보로 변환했습니다.",
        data=transform_service.transform_raw_event(db, auth, raw_event_id=event_id),
    )


@router.post("/accounts/{account_id}/raw-events/transform", response_model=ApiResult)
def transform_channel_account_raw_events_api(
    account_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_ready(auth)
    return api_success(
        result_code="CHANNEL_RAW_EVENTS_TRANSFORMED",
        message="채널 계정의 원본 이벤트를 반품접수 후보로 변환했습니다.",
        data=transform_service.transform_account_raw_events(db, auth, account_id=account_id),
    )


@router.post("/accounts/{account_id}/return-candidates/create-return-expected", response_model=ApiResult)
def create_return_expected_from_channel_account_api(
    account_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_ready(auth)
    return api_success(
        result_code="CHANNEL_RETURN_EXPECTED_BULK_CREATED",
        message="채널 반품 후보를 기존 반품처리 대기 row로 연결했습니다.",
        data=transform_service.create_account_return_expected(db, auth, account_id=account_id),
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


@router.get("/return-candidates", response_model=ApiResult)
def list_channel_return_candidates_api(
    account_id: int | None = None,
    match_status: str | None = None,
    correction_status: str | None = None,
    return_expected_create_status: str | None = None,
    channel_type: str | None = None,
    client_id: int | None = None,
    client_unit_id: int | None = None,
    has_return_tracking_no: bool | None = None,
    has_product: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    keyword: str | None = None,
    sort_by: str | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_ready(auth)
    return api_success(
        result_code="CHANNEL_RETURN_CANDIDATES_FOUND",
        message="채널 반품접수 후보 목록을 조회했습니다.",
        data=transform_service.list_candidates(
            db,
            auth,
            account_id=account_id,
            match_status=match_status,
            correction_status=correction_status,
            return_expected_create_status=return_expected_create_status,
            channel_type=channel_type,
            client_id=client_id,
            client_unit_id=client_unit_id,
            has_return_tracking_no=has_return_tracking_no,
            has_product=has_product,
            date_from=date_from,
            date_to=date_to,
            keyword=keyword,
            sort_by=sort_by,
        ),
    )


@router.get("/product-mappings", response_model=ApiResult)
def list_channel_product_mappings_api(
    client_id: int | None = None,
    channel_type: str | None = None,
    account_id: int | None = None,
    decision_type: str | None = None,
    conflict_only: bool = False,
    keyword: str | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_ready(auth)
    return api_success(
        result_code="CHANNEL_PRODUCT_MAPPINGS_FOUND",
        message="채널 상품 매핑 학습 목록을 조회했습니다.",
        data=transform_service.list_product_mappings(
            db,
            auth,
            client_id=client_id,
            channel_type=channel_type,
            account_id=account_id,
            decision_type=decision_type,
            conflict_only=conflict_only,
            keyword=keyword,
        ),
    )


@router.get("/return-candidates/{candidate_id}", response_model=ApiResult)
def get_channel_return_candidate_api(
    candidate_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_ready(auth)
    return api_success(
        result_code="CHANNEL_RETURN_CANDIDATE_FOUND",
        message="채널 반품접수 후보를 조회했습니다.",
        data=transform_service.get_candidate(db, auth, candidate_id=candidate_id),
    )


@router.post("/return-candidates/{candidate_id}/reprocess", response_model=ApiResult)
def reprocess_channel_return_candidate_api(
    candidate_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_ready(auth)
    return api_success(
        result_code="CHANNEL_RETURN_CANDIDATE_REPROCESSED",
        message="채널 반품접수 후보를 재처리했습니다.",
        data=transform_service.reprocess_candidate(db, auth, candidate_id=candidate_id),
    )


@router.patch("/return-candidates/{candidate_id}/correction", response_model=ApiResult)
def update_channel_return_candidate_correction_api(
    candidate_id: int,
    request: ChannelReturnCandidateCorrectionRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_ready(auth)
    return api_success(
        result_code="CHANNEL_RETURN_CANDIDATE_CORRECTION_SAVED",
        message="채널 반품접수 후보 보정값을 저장했습니다.",
        data=transform_service.save_correction(db, auth, candidate_id=candidate_id, request=request),
    )


@router.post("/return-candidates/{candidate_id}/clear-correction", response_model=ApiResult)
def clear_channel_return_candidate_correction_api(
    candidate_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_ready(auth)
    return api_success(
        result_code="CHANNEL_RETURN_CANDIDATE_CORRECTION_CLEARED",
        message="채널 반품접수 후보 보정값을 초기화했습니다.",
        data=transform_service.clear_correction(db, auth, candidate_id=candidate_id),
    )


@router.post("/return-candidates/{candidate_id}/mark-reviewed", response_model=ApiResult)
def mark_channel_return_candidate_reviewed_api(
    candidate_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_ready(auth)
    return api_success(
        result_code="CHANNEL_RETURN_CANDIDATE_REVIEWED",
        message="채널 반품접수 후보를 확인 처리했습니다.",
        data=transform_service.mark_reviewed(db, auth, candidate_id=candidate_id),
    )


@router.post("/return-candidates/{candidate_id}/create-return-expected", response_model=ApiResult)
def create_return_expected_from_channel_candidate_api(
    candidate_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth_context),
) -> ApiResult:
    _require_ready(auth)
    return api_success(
        result_code="CHANNEL_RETURN_EXPECTED_CREATED",
        message="채널 반품 후보를 기존 반품처리 대기 row로 연결했습니다.",
        data=transform_service.create_return_expected(db, auth, candidate_id=candidate_id),
    )
