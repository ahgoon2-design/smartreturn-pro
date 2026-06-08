from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.auth_context import resolve_effective_client_id
from app.core.exceptions import AuthError, ClientScopeDeniedError
from app.core.permissions import require_permission, require_roles
from app.repositories import channel_repository as repo
from app.repositories import master_repository
from app.schemas.auth import AuthContext
from app.schemas.channels import (
    ChannelAccountCreateRequest,
    ChannelAccountResponse,
    ChannelAccountsResponse,
    ChannelAccountUpdateRequest,
    ChannelConnectionTestResponse,
    ChannelRawEventDetailResponse,
    ChannelRawEventListItem,
    ChannelRawEventsResponse,
    ChannelSyncDryRunRequest,
    ChannelSyncDryRunResponse,
    ChannelSyncJobResponse,
    ChannelSyncJobsResponse,
)


CHANNEL_MANAGE_ROLES = {"SUPER_ADMIN", "INTERNAL_ADMIN"}
CHANNEL_VIEW_PERMISSION = "RETURN_VIEW"
CHANNEL_MANAGE_PERMISSION = "RETURN_MANAGE"
SAFE_CREDENTIAL_PLACEHOLDER = "credential-ref-not-configured"


def _business_error(result_code: str, message: str, status_code: int = 400) -> AuthError:
    return AuthError(message, result_code=result_code, status_code=status_code)


def _require_channel_view(auth: AuthContext) -> None:
    require_permission(auth, CHANNEL_VIEW_PERMISSION)


def _require_channel_manage(auth: AuthContext) -> None:
    require_roles(auth, CHANNEL_MANAGE_ROLES)
    require_permission(auth, CHANNEL_MANAGE_PERMISSION)


def _safe_error_message(message: str | None) -> str | None:
    if not message:
        return None
    return str(message).replace("\n", " ").replace("\r", " ")[:300]


def _mask_credential_ref(value: str | None) -> str | None:
    if not value:
        return None
    value = str(value).strip()
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}***{value[-4:]}"


def _raw_hash(raw_json: dict) -> str:
    payload = json.dumps(raw_json, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _tracking_hash(value: str | None) -> str | None:
    if not value:
        return None
    normalized = "".join(ch for ch in str(value) if ch.isalnum())
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _account_response(account) -> ChannelAccountResponse:
    return ChannelAccountResponse(
        id=account.id,
        client_id=account.client_id,
        client_unit_id=account.client_unit_id,
        channel_type=account.channel_type,
        account_name=account.account_name,
        store_name=account.store_name,
        external_account_id=account.external_account_id,
        status=account.status,
        auth_status=account.auth_status,
        credential_ref_masked=_mask_credential_ref(account.credential_ref),
        last_sync_at=account.last_sync_at,
        last_success_sync_at=account.last_success_sync_at,
        last_error_at=account.last_error_at,
        last_error_code=account.last_error_code,
        last_error_message=account.last_error_message,
        sync_enabled=account.sync_enabled,
        created_by=account.created_by,
        updated_by=account.updated_by,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


def _sync_job_response(job) -> ChannelSyncJobResponse:
    return ChannelSyncJobResponse(
        id=job.id,
        channel_account_id=job.channel_account_id,
        job_type=job.job_type,
        status=job.status,
        cursor_from=job.cursor_from,
        cursor_to=job.cursor_to,
        cursor_more_from=job.cursor_more_from,
        cursor_more_sequence=job.cursor_more_sequence,
        total_collected=job.total_collected,
        total_inserted=job.total_inserted,
        total_updated=job.total_updated,
        total_skipped=job.total_skipped,
        total_failed=job.total_failed,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error_code=job.error_code,
        error_message=job.error_message,
        created_at=job.created_at,
    )


def _raw_event_list_item(event) -> ChannelRawEventListItem:
    return ChannelRawEventListItem(
        id=event.id,
        channel_account_id=event.channel_account_id,
        channel_type=event.channel_type,
        event_type=event.event_type,
        external_order_id=event.external_order_id,
        external_product_order_id=event.external_product_order_id,
        external_claim_id=event.external_claim_id,
        external_tracking_no_hash=event.external_tracking_no_hash,
        last_changed_at=event.last_changed_at,
        raw_hash=event.raw_hash,
        process_status=event.process_status,
        process_error_code=event.process_error_code,
        process_error_message=event.process_error_message,
        collected_at=event.collected_at,
        created_at=event.created_at,
    )


class ChannelProvider(Protocol):
    provider_name: str

    def test_connection(self, account) -> dict:
        ...

    def collect_changed_orders(self, account) -> list[dict]:
        ...

    def collect_return_claims(self, account) -> list[dict]:
        ...


class NaverSmartStoreProvider:
    provider_name = "NAVER_SMARTSTORE_DRY_RUN"

    def test_connection(self, account) -> dict:
        return {
            "success": True,
            "status": "ACTIVE" if account.credential_ref else "AUTH_REQUIRED",
            "auth_status": "CONNECTED" if account.credential_ref else "NOT_CONNECTED",
            "message": "실제 네이버 API 호출 없이 dry-run 연결 구조만 확인했습니다.",
        }

    def collect_changed_orders(self, account) -> list[dict]:
        return self.collect_return_claims(account)

    def collect_return_claims(self, account) -> list[dict]:
        now = datetime.now(timezone.utc)
        raw_json = {
            "channel": "NAVER_SMARTSTORE",
            "eventType": "RETURN_CLAIM",
            "productOrderId": f"DRY-{account.id}-PRODUCT-ORDER",
            "orderId": f"DRY-{account.id}-ORDER",
            "claimId": f"DRY-{account.id}-CLAIM",
            "claimStatus": "RETURN_REQUESTED",
            "claimReason": "dry-run",
            "productName": "Dry-run 상품",
            "optionName": "기본",
            "qty": 1,
            "returnTrackingNoPresent": True,
        }
        return [
            {
                "event_type": "RETURN_CLAIM",
                "external_order_id": raw_json["orderId"],
                "external_product_order_id": raw_json["productOrderId"],
                "external_claim_id": raw_json["claimId"],
                "external_tracking_no_hash": _tracking_hash(f"DRY-RETURN-{account.id}"),
                "last_changed_at": now,
                "raw_json": raw_json,
                "raw_hash": _raw_hash(raw_json),
                "process_status": "RECEIVED",
                "collected_at": now,
            }
        ]


def _provider_for(account) -> ChannelProvider:
    if account.channel_type == "NAVER_SMARTSTORE":
        return NaverSmartStoreProvider()
    return NaverSmartStoreProvider()


class ChannelAccountService:
    def list_accounts(
        self,
        db: Session,
        auth: AuthContext,
        *,
        client_id: int | None = None,
        channel_type: str | None = None,
        include_inactive: bool = False,
    ) -> dict:
        _require_channel_view(auth)
        effective_client_id = resolve_effective_client_id(auth, client_id, allow_all_clients=True)
        rows = repo.list_channel_accounts(
            db,
            client_id=effective_client_id,
            channel_type=channel_type,
            include_inactive=include_inactive,
        )
        return ChannelAccountsResponse(items=[_account_response(row) for row in rows]).model_dump()

    def get_account(self, db: Session, auth: AuthContext, *, account_id: int) -> dict:
        _require_channel_view(auth)
        account = self._get_scoped_account(db, auth, account_id=account_id)
        return _account_response(account).model_dump()

    def create_account(self, db: Session, auth: AuthContext, request: ChannelAccountCreateRequest) -> dict:
        _require_channel_manage(auth)
        client_id = resolve_effective_client_id(auth, request.client_id)
        self._ensure_client_and_unit(db, client_id=client_id, client_unit_id=request.client_unit_id)
        credential_ref = self._safe_credential_ref(request.credential_ref)
        account = repo.create_channel_account(
            db,
            client_id=client_id,
            client_unit_id=request.client_unit_id,
            channel_type=request.channel_type,
            account_name=request.account_name,
            store_name=request.store_name,
            external_account_id=request.external_account_id,
            credential_ref=credential_ref,
            status="ACTIVE" if credential_ref else "AUTH_REQUIRED",
            auth_status="CONNECTED" if credential_ref else "NOT_CONNECTED",
            sync_enabled=request.sync_enabled,
            created_by=auth.user_id,
            updated_by=auth.user_id,
        )
        db.commit()
        return _account_response(account).model_dump()

    def update_account(self, db: Session, auth: AuthContext, *, account_id: int, request: ChannelAccountUpdateRequest) -> dict:
        _require_channel_manage(auth)
        account = self._get_scoped_account(db, auth, account_id=account_id)
        values = request.model_dump(exclude_unset=True)
        if "client_unit_id" in values:
            self._ensure_client_and_unit(db, client_id=account.client_id, client_unit_id=values["client_unit_id"])
        if "credential_ref" in values:
            values["credential_ref"] = self._safe_credential_ref(values["credential_ref"])
        values["updated_by"] = auth.user_id
        account = repo.update_channel_account(db, account, values)
        db.commit()
        return _account_response(account).model_dump()

    def disable_account(self, db: Session, auth: AuthContext, *, account_id: int) -> dict:
        _require_channel_manage(auth)
        account = self._get_scoped_account(db, auth, account_id=account_id)
        account = repo.update_channel_account(
            db,
            account,
            {
                "status": "INACTIVE",
                "sync_enabled": False,
                "updated_by": auth.user_id,
            },
        )
        db.commit()
        return _account_response(account).model_dump()

    def test_connection_dry_run(self, db: Session, auth: AuthContext, *, account_id: int) -> dict:
        _require_channel_manage(auth)
        account = self._get_scoped_account(db, auth, account_id=account_id)
        provider = _provider_for(account)
        result = provider.test_connection(account)
        account = repo.update_channel_account(
            db,
            account,
            {
                "status": result["status"],
                "auth_status": result["auth_status"],
                "last_error_code": None,
                "last_error_message": None,
                "updated_by": auth.user_id,
            },
        )
        db.commit()
        return ChannelConnectionTestResponse(
            channel_account_id=account.id,
            channel_type=account.channel_type,
            success=bool(result["success"]),
            status=account.status,
            auth_status=account.auth_status,
            message=result["message"],
            provider_name=provider.provider_name,
        ).model_dump()

    def _get_scoped_account(self, db: Session, auth: AuthContext, *, account_id: int):
        account = repo.get_channel_account(db, account_id)
        if account is None:
            raise _business_error("CHANNEL_ACCOUNT_NOT_FOUND", "채널 계정을 찾을 수 없습니다.", 404)
        resolve_effective_client_id(auth, account.client_id)
        return account

    def _ensure_client_and_unit(self, db: Session, *, client_id: int, client_unit_id: int | None):
        if master_repository.get_client_by_id(db, client_id) is None:
            raise _business_error("CHANNEL_CLIENT_NOT_FOUND", "고객사를 찾을 수 없습니다.", 404)
        if client_unit_id is None:
            return
        unit = master_repository.get_client_unit_by_id(db, client_unit_id)
        if unit is None or unit.client_id != client_id:
            raise ClientScopeDeniedError("다른 고객사의 운영단위는 채널 계정에 연결할 수 없습니다.")

    def _safe_credential_ref(self, credential_ref: str | None) -> str | None:
        if credential_ref is None:
            return None
        value = str(credential_ref).strip()
        if not value:
            return None
        lower = value.lower()
        if lower.startswith(("sk-", "token", "password", "secret")):
            raise _business_error("CHANNEL_CREDENTIAL_REF_UNSAFE", "실제 secret/token 값은 저장할 수 없습니다.")
        return value


class ChannelSyncService:
    def start_dry_run_job(
        self,
        db: Session,
        auth: AuthContext,
        *,
        account_id: int,
        request: ChannelSyncDryRunRequest,
    ) -> dict:
        _require_channel_manage(auth)
        account = account_service._get_scoped_account(db, auth, account_id=account_id)
        provider = _provider_for(account)
        now = datetime.now(timezone.utc)
        job = repo.create_channel_sync_job(
            db,
            channel_account_id=account.id,
            job_type=request.job_type,
            status="RUNNING",
            started_at=now,
            cursor_more_from="DRY_RUN",
            cursor_more_sequence="0",
        )
        try:
            provider_events = self.collect_changed_orders_dry_run(provider, account) if request.save_mock_event else []
            inserted = 0
            updated = 0
            for event in provider_events:
                _raw_event, created = self.upsert_raw_event_by_hash_or_external_keys(db, account=account, event=event)
                if created:
                    inserted += 1
                else:
                    updated += 1
            finished_at = datetime.now(timezone.utc)
            job = repo.update_channel_sync_job(
                db,
                job,
                {
                    "status": "SUCCESS",
                    "total_collected": len(provider_events),
                    "total_inserted": inserted,
                    "total_updated": updated,
                    "total_skipped": 0,
                    "total_failed": 0,
                    "finished_at": finished_at,
                    "cursor_to": finished_at.isoformat(),
                },
            )
            repo.update_channel_account(
                db,
                account,
                {
                    "last_sync_at": finished_at,
                    "last_success_sync_at": finished_at,
                    "last_error_at": None,
                    "last_error_code": None,
                    "last_error_message": None,
                    "updated_by": auth.user_id,
                },
            )
            db.commit()
            return ChannelSyncDryRunResponse(
                job=_sync_job_response(job),
                provider_name=provider.provider_name,
                collected_event_count=len(provider_events),
                inserted_event_count=inserted,
                updated_event_count=updated,
                skipped_event_count=0,
                message="실제 채널 API 호출 없이 dry-run 수집 job을 생성했습니다.",
            ).model_dump()
        except Exception as exc:
            safe_message = _safe_error_message(str(exc)) or "dry-run 수집 실패"
            finished_at = datetime.now(timezone.utc)
            repo.update_channel_sync_job(
                db,
                job,
                {
                    "status": "FAILED",
                    "total_failed": 1,
                    "finished_at": finished_at,
                    "error_code": "CHANNEL_DRY_RUN_FAILED",
                    "error_message": safe_message,
                },
            )
            repo.update_channel_account(
                db,
                account,
                {
                    "last_sync_at": finished_at,
                    "last_error_at": finished_at,
                    "last_error_code": "CHANNEL_DRY_RUN_FAILED",
                    "last_error_message": safe_message,
                    "updated_by": auth.user_id,
                },
            )
            db.commit()
            raise

    def collect_changed_orders_dry_run(self, provider: ChannelProvider, account) -> list[dict]:
        return provider.collect_changed_orders(account)

    def save_raw_event(self, db: Session, *, account, event: dict):
        return self.upsert_raw_event_by_hash_or_external_keys(db, account=account, event=event)

    def upsert_raw_event_by_hash_or_external_keys(self, db: Session, *, account, event: dict):
        return repo.upsert_channel_raw_event(db, account=account, event=event)

    def list_sync_jobs(self, db: Session, auth: AuthContext, *, account_id: int | None = None) -> dict:
        _require_channel_view(auth)
        if account_id is not None:
            account_service._get_scoped_account(db, auth, account_id=account_id)
            rows = repo.list_channel_sync_jobs(db, account_id=account_id)
        else:
            effective_client_id = resolve_effective_client_id(auth, None, allow_all_clients=True)
            accounts = repo.list_channel_accounts(db, client_id=effective_client_id, include_inactive=True)
            account_ids = {account.id for account in accounts}
            rows = [job for job in repo.list_channel_sync_jobs(db, limit=100) if job.channel_account_id in account_ids]
        return ChannelSyncJobsResponse(items=[_sync_job_response(row) for row in rows]).model_dump()

    def list_raw_events(
        self,
        db: Session,
        auth: AuthContext,
        *,
        account_id: int | None = None,
        process_status: str | None = None,
    ) -> dict:
        _require_channel_view(auth)
        effective_client_id = resolve_effective_client_id(auth, None, allow_all_clients=True)
        if account_id is not None:
            account_service._get_scoped_account(db, auth, account_id=account_id)
        rows = repo.list_channel_raw_events(
            db,
            client_id=effective_client_id,
            account_id=account_id,
            process_status=process_status,
        )
        return ChannelRawEventsResponse(items=[_raw_event_list_item(row) for row in rows]).model_dump()

    def get_raw_event(self, db: Session, auth: AuthContext, *, event_id: int) -> dict:
        _require_channel_view(auth)
        event = repo.get_channel_raw_event(db, event_id)
        if event is None:
            raise _business_error("CHANNEL_RAW_EVENT_NOT_FOUND", "채널 원본 이벤트를 찾을 수 없습니다.", 404)
        account_service._get_scoped_account(db, auth, account_id=event.channel_account_id)
        item = _raw_event_list_item(event)
        return ChannelRawEventDetailResponse(**item.model_dump(), raw_json=event.raw_json).model_dump()


account_service = ChannelAccountService()
sync_service = ChannelSyncService()
