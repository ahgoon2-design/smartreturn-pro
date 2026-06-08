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
    ChannelRawEventsBulkTransformResponse,
    ChannelRawEventTransformResponse,
    ChannelReturnCandidateActionResponse,
    ChannelReturnCandidateDetailResponse,
    ChannelReturnCandidateResponse,
    ChannelReturnCandidatesResponse,
    ChannelSyncDryRunRequest,
    ChannelSyncDryRunResponse,
    ChannelSyncJobResponse,
    ChannelSyncJobsResponse,
)


CHANNEL_MANAGE_ROLES = {"SUPER_ADMIN", "INTERNAL_ADMIN"}
CHANNEL_VIEW_PERMISSION = "RETURN_VIEW"
CHANNEL_MANAGE_PERMISSION = "RETURN_MANAGE"
SAFE_CREDENTIAL_PLACEHOLDER = "credential-ref-not-configured"
RETURN_CANDIDATE_STATUSES = (
    "READY_FOR_INTAKE",
    "TEAM_ASSIGN_PENDING",
    "PRODUCT_MATCH_PENDING",
    "RETURN_TRACKING_PENDING",
    "NEEDS_REVIEW",
    "BLOCKED",
)


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


def _candidate_response(candidate) -> ChannelReturnCandidateResponse:
    return ChannelReturnCandidateResponse(
        id=candidate.id,
        channel_raw_event_id=candidate.channel_raw_event_id,
        channel_account_id=candidate.channel_account_id,
        client_id=candidate.client_id,
        client_unit_id=candidate.client_unit_id,
        source_type=candidate.source_type,
        source_origin=candidate.source_origin,
        external_order_id=candidate.external_order_id,
        external_product_order_id=candidate.external_product_order_id,
        external_claim_id=candidate.external_claim_id,
        return_tracking_no=candidate.return_tracking_no,
        original_tracking_no=candidate.original_tracking_no,
        tracking_no_for_scan=candidate.tracking_no_for_scan,
        product_code=candidate.product_code,
        barcode=candidate.barcode,
        product_id=candidate.product_id,
        product_name=candidate.product_name,
        option_name=candidate.option_name,
        qty=candidate.qty,
        claim_reason=candidate.claim_reason,
        claim_status=candidate.claim_status,
        match_status=candidate.match_status,
        match_reason=candidate.match_reason,
        risk_flags=list(candidate.risk_flags_json or []),
        reviewed_at=candidate.reviewed_at,
        reviewed_by=candidate.reviewed_by,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
    )


def _candidate_summary(candidates: list) -> dict[str, int]:
    summary = {status: 0 for status in RETURN_CANDIDATE_STATUSES}
    for candidate in candidates:
        summary[candidate.match_status] = summary.get(candidate.match_status, 0) + 1
    return summary


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


class ChannelCanonicalTransformer(Protocol):
    transformer_name: str

    def transform(self, raw_event, account) -> dict:
        ...


class NaverReturnCanonicalTransformer:
    transformer_name = "NAVER_RETURN_CANONICAL_TRANSFORMER"

    def transform(self, raw_event, account) -> dict:
        raw_json = raw_event.raw_json
        if not isinstance(raw_json, dict):
            return _blocked_payload(raw_event, account, "raw_json 구조가 올바르지 않습니다.", ["RAW_JSON_INVALID"])

        external_order_id = _first_text(raw_event.external_order_id, raw_json.get("orderId"), raw_json.get("order_id"))
        external_product_order_id = _first_text(
            raw_event.external_product_order_id,
            raw_json.get("productOrderId"),
            raw_json.get("product_order_id"),
        )
        external_claim_id = _first_text(raw_event.external_claim_id, raw_json.get("claimId"), raw_json.get("claim_id"))
        return_tracking_no = _normalize_tracking_no(
            _first_text(
                raw_json.get("returnTrackingNo"),
                raw_json.get("return_tracking_no"),
                raw_json.get("collectTrackingNo"),
                raw_json.get("returnInvoiceNo"),
            )
        )
        original_tracking_no = _normalize_tracking_no(
            _first_text(
                raw_json.get("originalTrackingNo"),
                raw_json.get("original_tracking_no"),
                raw_json.get("deliveryTrackingNo"),
                raw_json.get("outboundTrackingNo"),
            )
        )
        product_code = _first_text(
            raw_json.get("sellerProductCode"),
            raw_json.get("seller_product_code"),
            raw_json.get("sku"),
            raw_json.get("SKU"),
            raw_json.get("productCode"),
        )
        barcode = _first_text(raw_json.get("barcode"), raw_json.get("productBarcode"))
        qty = _normalize_qty(raw_json.get("qty") or raw_json.get("quantity") or raw_json.get("claimQty"))
        product_name = _first_text(raw_json.get("productName"), raw_json.get("product_name"))
        option_name = _first_text(raw_json.get("optionName"), raw_json.get("option_name"))
        claim_reason = _first_text(raw_json.get("claimReason"), raw_json.get("claim_reason"))
        claim_status = _first_text(raw_json.get("claimStatus"), raw_json.get("claim_status"))

        canonical_json = {
            "source_type": "CHANNEL_API",
            "source_origin": account.channel_type,
            "external_order_id": external_order_id,
            "external_product_order_id": external_product_order_id,
            "external_claim_id": external_claim_id,
            "return_tracking_no_present": bool(return_tracking_no),
            "original_tracking_no_present": bool(original_tracking_no),
            "tracking_no_for_scan_present": bool(return_tracking_no),
            "product_code": product_code,
            "barcode_present": bool(barcode),
            "product_name": product_name,
            "option_name": option_name,
            "qty": qty,
            "claim_reason": claim_reason,
            "claim_status": claim_status,
        }
        return {
            "source_type": "CHANNEL_API",
            "source_origin": account.channel_type,
            "external_order_id": external_order_id,
            "external_product_order_id": external_product_order_id,
            "external_claim_id": external_claim_id,
            "return_tracking_no": return_tracking_no,
            "original_tracking_no": original_tracking_no,
            "tracking_no_for_scan": return_tracking_no,
            "product_code": product_code,
            "barcode": barcode,
            "product_id": None,
            "product_name": product_name,
            "option_name": option_name,
            "qty": qty,
            "claim_reason": claim_reason,
            "claim_status": claim_status,
            "canonical_json": canonical_json,
            "risk_flags_json": [],
        }


def _provider_for(account) -> ChannelProvider:
    if account.channel_type == "NAVER_SMARTSTORE":
        return NaverSmartStoreProvider()
    return NaverSmartStoreProvider()


def _transformer_for(raw_event) -> ChannelCanonicalTransformer:
    if raw_event.channel_type == "NAVER_SMARTSTORE":
        return NaverReturnCanonicalTransformer()
    return NaverReturnCanonicalTransformer()


def _blocked_payload(raw_event, account, reason: str, risk_flags: list[str]) -> dict:
    return {
        "source_type": "CHANNEL_API",
        "source_origin": account.channel_type,
        "external_order_id": raw_event.external_order_id,
        "external_product_order_id": raw_event.external_product_order_id,
        "external_claim_id": raw_event.external_claim_id,
        "return_tracking_no": None,
        "original_tracking_no": None,
        "tracking_no_for_scan": None,
        "product_code": None,
        "barcode": None,
        "product_id": None,
        "product_name": None,
        "option_name": None,
        "qty": None,
        "claim_reason": None,
        "claim_status": None,
        "canonical_json": {"source_type": "CHANNEL_API", "source_origin": account.channel_type, "blocked": True},
        "match_status": "BLOCKED",
        "match_reason": reason,
        "risk_flags_json": risk_flags,
    }


def _first_text(*values) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text[:255]
    return None


def _normalize_tracking_no(value: str | None) -> str | None:
    if not value:
        return None
    normalized = "".join(ch for ch in str(value).strip() if ch.isalnum())
    return normalized[:100] or None


def _normalize_barcode(value: str | None) -> str | None:
    if not value:
        return None
    normalized = "".join(ch for ch in str(value).strip() if ch.isalnum()).upper()
    return normalized[:100] or None


def _normalize_qty(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        qty = int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None
    return qty if qty > 0 else None


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


class ChannelCanonicalTransformService:
    def transform_raw_event(self, db: Session, auth: AuthContext, *, raw_event_id: int) -> dict:
        _require_channel_manage(auth)
        raw_event = repo.get_channel_raw_event(db, raw_event_id)
        if raw_event is None:
            raise _business_error("CHANNEL_RAW_EVENT_NOT_FOUND", "채널 원본 이벤트를 찾을 수 없습니다.", 404)
        account = account_service._get_scoped_account(db, auth, account_id=raw_event.channel_account_id)
        candidate, created = self._transform_and_save(db, raw_event=raw_event, account=account, reviewed_by=None)
        db.commit()
        return ChannelRawEventTransformResponse(
            candidate=_candidate_response(candidate),
            created=created,
            message="채널 원본 이벤트를 반품접수 후보로 변환했습니다.",
        ).model_dump()

    def transform_account_raw_events(self, db: Session, auth: AuthContext, *, account_id: int) -> dict:
        _require_channel_manage(auth)
        account = account_service._get_scoped_account(db, auth, account_id=account_id)
        rows = repo.list_channel_raw_events(db, account_id=account.id, process_status=None, limit=200)
        candidates = []
        created_count = 0
        updated_count = 0
        failed_count = 0
        for raw_event in rows:
            try:
                candidate, created = self._transform_and_save(db, raw_event=raw_event, account=account, reviewed_by=None)
                candidates.append(candidate)
                if created:
                    created_count += 1
                else:
                    updated_count += 1
            except Exception as exc:
                failed_count += 1
                repo.update_channel_raw_event(
                    db,
                    raw_event,
                    {
                        "process_status": "FAILED",
                        "process_error_code": "CHANNEL_TRANSFORM_FAILED",
                        "process_error_message": _safe_error_message(str(exc)),
                    },
                )
        db.commit()
        return ChannelRawEventsBulkTransformResponse(
            transformed_count=len(candidates),
            created_count=created_count,
            updated_count=updated_count,
            failed_count=failed_count,
            candidates=[_candidate_response(candidate) for candidate in candidates],
            summary=_candidate_summary(candidates),
        ).model_dump()

    def list_candidates(
        self,
        db: Session,
        auth: AuthContext,
        *,
        account_id: int | None = None,
        match_status: str | None = None,
    ) -> dict:
        _require_channel_view(auth)
        effective_client_id = resolve_effective_client_id(auth, None, allow_all_clients=True)
        if account_id is not None:
            account_service._get_scoped_account(db, auth, account_id=account_id)
        rows = repo.list_channel_return_candidates(
            db,
            client_id=effective_client_id,
            account_id=account_id,
            match_status=match_status,
            limit=200,
        )
        return ChannelReturnCandidatesResponse(
            items=[_candidate_response(candidate) for candidate in rows],
            summary=_candidate_summary(rows),
        ).model_dump()

    def get_candidate(self, db: Session, auth: AuthContext, *, candidate_id: int) -> dict:
        _require_channel_view(auth)
        candidate = self._get_scoped_candidate(db, auth, candidate_id=candidate_id)
        item = _candidate_response(candidate)
        return ChannelReturnCandidateDetailResponse(**item.model_dump(), canonical_json=candidate.canonical_json).model_dump()

    def reprocess_candidate(self, db: Session, auth: AuthContext, *, candidate_id: int) -> dict:
        _require_channel_manage(auth)
        candidate = self._get_scoped_candidate(db, auth, candidate_id=candidate_id)
        raw_event = repo.get_channel_raw_event(db, candidate.channel_raw_event_id)
        if raw_event is None:
            raise _business_error("CHANNEL_RAW_EVENT_NOT_FOUND", "채널 원본 이벤트를 찾을 수 없습니다.", 404)
        account = account_service._get_scoped_account(db, auth, account_id=candidate.channel_account_id)
        new_candidate, _created = self._transform_and_save(db, raw_event=raw_event, account=account, reviewed_by=None)
        db.commit()
        return ChannelReturnCandidateActionResponse(
            candidate=_candidate_response(new_candidate),
            message="반품접수 후보를 재처리했습니다.",
        ).model_dump()

    def mark_reviewed(self, db: Session, auth: AuthContext, *, candidate_id: int) -> dict:
        _require_channel_manage(auth)
        candidate = self._get_scoped_candidate(db, auth, candidate_id=candidate_id)
        now = datetime.now(timezone.utc)
        candidate = repo.upsert_channel_return_candidate(
            db,
            raw_event=repo.get_channel_raw_event(db, candidate.channel_raw_event_id),
            account=account_service._get_scoped_account(db, auth, account_id=candidate.channel_account_id),
            values={
                "client_unit_id": candidate.client_unit_id,
                "source_type": candidate.source_type,
                "source_origin": candidate.source_origin,
                "external_order_id": candidate.external_order_id,
                "external_product_order_id": candidate.external_product_order_id,
                "external_claim_id": candidate.external_claim_id,
                "return_tracking_no": candidate.return_tracking_no,
                "original_tracking_no": candidate.original_tracking_no,
                "tracking_no_for_scan": candidate.tracking_no_for_scan,
                "product_code": candidate.product_code,
                "barcode": candidate.barcode,
                "product_id": candidate.product_id,
                "product_name": candidate.product_name,
                "option_name": candidate.option_name,
                "qty": candidate.qty,
                "claim_reason": candidate.claim_reason,
                "claim_status": candidate.claim_status,
                "canonical_json": candidate.canonical_json,
                "match_status": candidate.match_status,
                "match_reason": candidate.match_reason,
                "risk_flags_json": candidate.risk_flags_json,
                "reviewed_at": now,
                "reviewed_by": auth.user_id,
            },
        )[0]
        db.commit()
        return ChannelReturnCandidateActionResponse(
            candidate=_candidate_response(candidate),
            message="반품접수 후보를 확인 처리했습니다.",
        ).model_dump()

    def create_return_expected(self, db: Session, auth: AuthContext, *, candidate_id: int) -> dict:
        _require_channel_manage(auth)
        candidate = self._get_scoped_candidate(db, auth, candidate_id=candidate_id)
        return ChannelReturnCandidateActionResponse(
            candidate=_candidate_response(candidate),
            message="반품예정자료 생성은 다음 단계에서 기존 반품접수 원장 계약에 맞춰 연결합니다.",
        ).model_dump()

    def _transform_and_save(self, db: Session, *, raw_event, account, reviewed_by: int | None):
        transformer = _transformer_for(raw_event)
        values = transformer.transform(raw_event, account)
        values = self._apply_matching_and_status(db, raw_event=raw_event, account=account, values=values)
        existing = repo.get_channel_return_candidate_by_raw_event(db, raw_event.id)
        conflicts = repo.find_candidate_conflicts(
            db,
            client_id=account.client_id,
            return_tracking_no=values.get("return_tracking_no"),
            external_product_order_id=values.get("external_product_order_id"),
            external_claim_id=values.get("external_claim_id"),
            exclude_candidate_id=existing.id if existing else None,
        )
        if conflicts and values["match_status"] != "BLOCKED":
            risks = list(values.get("risk_flags_json") or [])
            risks.append("RETURN_TRACKING_CONFLICT")
            values["match_status"] = "NEEDS_REVIEW"
            values["match_reason"] = "같은 반품송장이 다른 외부 주문/클레임 후보와 충돌합니다."
            values["risk_flags_json"] = sorted(set(risks))
        if reviewed_by is not None:
            values["reviewed_at"] = datetime.now(timezone.utc)
            values["reviewed_by"] = reviewed_by
        candidate, created = repo.upsert_channel_return_candidate(db, raw_event=raw_event, account=account, values=values)
        repo.update_channel_raw_event(
            db,
            raw_event,
            {
                "process_status": "FAILED" if candidate.match_status == "BLOCKED" else "NORMALIZED",
                "process_error_code": "CHANNEL_CANDIDATE_BLOCKED" if candidate.match_status == "BLOCKED" else None,
                "process_error_message": candidate.match_reason if candidate.match_status == "BLOCKED" else None,
            },
        )
        return candidate, created

    def _apply_matching_and_status(self, db: Session, *, raw_event, account, values: dict) -> dict:
        if values.get("match_status") == "BLOCKED":
            return values
        risks: list[str] = list(values.get("risk_flags_json") or [])
        reasons: list[str] = []

        if not values.get("external_product_order_id") and not values.get("external_claim_id") and not values.get("return_tracking_no") and not values.get("original_tracking_no"):
            values["match_status"] = "BLOCKED"
            values["match_reason"] = "외부 식별자와 송장 후보가 없어 추적할 수 없습니다."
            values["risk_flags_json"] = ["MISSING_EXTERNAL_IDENTIFIER"]
            return values

        product = self._match_product(db, account.client_id, values)
        if product is not None:
            values["product_id"] = product.id
            values["product_code"] = product.product_code
        else:
            risks.append("PRODUCT_MATCH_REQUIRED")
            reasons.append("상품마스터 매칭이 필요합니다.")

        if account.client_unit_id:
            values["client_unit_id"] = account.client_unit_id
        else:
            values["client_unit_id"] = None
            risks.append("TEAM_ASSIGN_REQUIRED")
            reasons.append("팀/운영단위 배정이 필요합니다.")

        if values.get("return_tracking_no"):
            values["tracking_no_for_scan"] = values["return_tracking_no"]
        elif values.get("original_tracking_no"):
            values["tracking_no_for_scan"] = None
            risks.append("RETURN_TRACKING_REQUIRED")
            reasons.append("반품송장이 없어 원송장은 보조 조회 후보로만 둡니다.")
        else:
            values["tracking_no_for_scan"] = None
            risks.append("RETURN_TRACKING_REQUIRED")
            reasons.append("반품 현장 스캔 기준 송장이 없습니다.")

        if values.get("qty") is None:
            risks.append("QTY_REQUIRED")
            reasons.append("수량 확인이 필요합니다.")

        if "RETURN_TRACKING_REQUIRED" in risks:
            status = "RETURN_TRACKING_PENDING"
            reason = "반품송장 확인이 필요합니다."
        elif "TEAM_ASSIGN_REQUIRED" in risks:
            status = "TEAM_ASSIGN_PENDING"
            reason = "팀/운영단위 배정이 필요합니다."
        elif "PRODUCT_MATCH_REQUIRED" in risks:
            status = "PRODUCT_MATCH_PENDING"
            reason = "상품마스터 매칭이 필요합니다."
        elif "QTY_REQUIRED" in risks:
            status = "NEEDS_REVIEW"
            reason = "수량 확인이 필요합니다."
        else:
            status = "READY_FOR_INTAKE"
            reason = "고객사, 팀, 상품, 반품송장 기준이 확인되어 현장 스캔 처리 후보입니다."

        values["match_status"] = status
        values["match_reason"] = reason if not reasons else reason
        values["risk_flags_json"] = sorted(set(risks))
        return values

    def _match_product(self, db: Session, client_id: int, values: dict):
        product_code = _first_text(values.get("product_code"))
        if product_code:
            product = master_repository.find_product_by_code(db, client_id, product_code)
            if product is not None:
                return product
        barcode_norm = _normalize_barcode(values.get("barcode"))
        if barcode_norm:
            product = master_repository.find_product_by_barcode(db, client_id, barcode_norm)
            if product is not None:
                return product
            product_barcode = master_repository.find_product_barcode_by_norm(db, client_id, barcode_norm)
            if product_barcode is not None:
                return master_repository.get_product_by_id(db, product_barcode.product_id)
        return None

    def _get_scoped_candidate(self, db: Session, auth: AuthContext, *, candidate_id: int):
        candidate = repo.get_channel_return_candidate(db, candidate_id)
        if candidate is None:
            raise _business_error("CHANNEL_RETURN_CANDIDATE_NOT_FOUND", "채널 반품 후보를 찾을 수 없습니다.", 404)
        resolve_effective_client_id(auth, candidate.client_id)
        return candidate


account_service = ChannelAccountService()
sync_service = ChannelSyncService()
transform_service = ChannelCanonicalTransformService()
