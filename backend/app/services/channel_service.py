from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.auth_context import resolve_effective_client_id
from app.core.exceptions import AuthError, ClientScopeDeniedError
from app.core.permissions import require_permission, require_roles
from app.models.returns import ReturnIntakeRow
from app.repositories import channel_repository as repo
from app.repositories import master_repository
from app.repositories import return_intake_repository
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
    ChannelReturnCandidateCorrectionRequest,
    ChannelReturnCandidateDetailResponse,
    ChannelReturnCandidateResponse,
    ChannelReturnCandidatesResponse,
    ChannelReturnExpectedBulkCreateResponse,
    ChannelReturnExpectedCreateResponse,
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
RETURN_EXPECTED_NOT_CREATED = "NOT_CREATED"
RETURN_EXPECTED_CREATED = "CREATED"
RETURN_EXPECTED_SKIPPED_DUPLICATE = "SKIPPED_DUPLICATE"
RETURN_EXPECTED_FAILED = "FAILED"
RETURN_INTAKE_SOURCE_TYPE_CHANNEL_API = "CHANNEL_API"
RETURN_INTAKE_BATCH_STATUS_READY = "READY_FOR_PROCESSING"
RETURN_INTAKE_ROW_STATUS_READY = "READY_FOR_PROCESSING"
RETURN_INTAKE_ROW_VALID = "VALID"
RETURN_INTAKE_TEAM_ASSIGNED = "ASSIGNED"


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


def _norm_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = "".join(ch for ch in str(value).strip().upper() if ch.isalnum())
    return text[:255] or None


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
        manual_client_unit_id=candidate.manual_client_unit_id,
        manual_product_id=candidate.manual_product_id,
        manual_product_code=candidate.manual_product_code,
        manual_return_tracking_no=candidate.manual_return_tracking_no,
        manual_original_tracking_no=candidate.manual_original_tracking_no,
        manual_qty=candidate.manual_qty,
        manual_review_note=candidate.manual_review_note,
        manual_reviewed_by=candidate.manual_reviewed_by,
        manual_reviewed_at=candidate.manual_reviewed_at,
        correction_status=candidate.correction_status,
        correction_summary=dict(candidate.correction_json or {}),
        return_expected_id=candidate.return_expected_id,
        return_expected_created_at=candidate.return_expected_created_at,
        return_expected_create_status=candidate.return_expected_create_status,
        return_expected_create_error=candidate.return_expected_create_error,
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
        self._ensure_candidate_not_linked(candidate)
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

    def save_correction(
        self,
        db: Session,
        auth: AuthContext,
        *,
        candidate_id: int,
        request: ChannelReturnCandidateCorrectionRequest,
    ) -> dict:
        _require_channel_manage(auth)
        candidate = self._get_scoped_candidate(db, auth, candidate_id=candidate_id)
        self._ensure_candidate_not_linked(candidate)
        values = self._validate_correction_values(db, candidate, request)
        now = datetime.now(timezone.utc)
        values.update(
            {
                "manual_reviewed_by": auth.user_id,
                "manual_reviewed_at": now,
                "correction_status": "CORRECTED",
                "return_expected_create_status": RETURN_EXPECTED_NOT_CREATED,
                "return_expected_create_error": None,
            }
        )
        candidate = repo.update_channel_return_candidate(db, candidate, values)
        if candidate.manual_product_id is not None:
            self._save_product_channel_mapping(db, candidate, auth.user_id)
        db.commit()
        return ChannelReturnCandidateActionResponse(
            candidate=_candidate_response(candidate),
            message="수동 보정값을 저장했습니다. 재처리 후 READY 전환 여부를 확인하세요.",
        ).model_dump()

    def clear_correction(self, db: Session, auth: AuthContext, *, candidate_id: int) -> dict:
        _require_channel_manage(auth)
        candidate = self._get_scoped_candidate(db, auth, candidate_id=candidate_id)
        self._ensure_candidate_not_linked(candidate)
        candidate = repo.update_channel_return_candidate(
            db,
            candidate,
            {
                "manual_client_unit_id": None,
                "manual_product_id": None,
                "manual_product_code": None,
                "manual_return_tracking_no": None,
                "manual_original_tracking_no": None,
                "manual_qty": None,
                "manual_review_note": None,
                "manual_reviewed_by": None,
                "manual_reviewed_at": None,
                "correction_status": "NONE",
                "correction_json": None,
                "return_expected_create_status": RETURN_EXPECTED_NOT_CREATED,
                "return_expected_create_error": None,
            },
        )
        db.commit()
        return ChannelReturnCandidateActionResponse(
            candidate=_candidate_response(candidate),
            message="수동 보정값을 초기화했습니다.",
        ).model_dump()

    def mark_reviewed(self, db: Session, auth: AuthContext, *, candidate_id: int) -> dict:
        _require_channel_manage(auth)
        candidate = self._get_scoped_candidate(db, auth, candidate_id=candidate_id)
        self._ensure_candidate_not_linked(candidate)
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
                "correction_status": "REVIEWED",
                "correction_json": dict(candidate.correction_json or {}),
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
        candidate, created, skipped_duplicate, message = self._create_return_expected_from_candidate(
            db,
            auth,
            candidate,
        )
        db.commit()
        return ChannelReturnExpectedCreateResponse(
            candidate=_candidate_response(candidate),
            return_expected_id=candidate.return_expected_id,
            created=created,
            skipped_duplicate=skipped_duplicate,
            message=message,
        ).model_dump()

    def create_account_return_expected(self, db: Session, auth: AuthContext, *, account_id: int) -> dict:
        _require_channel_manage(auth)
        account = account_service._get_scoped_account(db, auth, account_id=account_id)
        candidates = repo.list_ready_candidates_for_return_expected(db, account_id=account.id, limit=200)
        created_count = 0
        skipped_duplicate_count = 0
        blocked_count = 0
        failed_count = 0
        created_candidate_ids: list[int] = []
        blocked_reasons: list[str] = []
        error_summary: list[str] = []
        changed_candidates = []

        for candidate in candidates:
            try:
                candidate, created, skipped_duplicate, message = self._create_return_expected_from_candidate(
                    db,
                    auth,
                    candidate,
                )
                changed_candidates.append(candidate)
                if created:
                    created_count += 1
                    created_candidate_ids.append(candidate.id)
                elif skipped_duplicate:
                    skipped_duplicate_count += 1
                else:
                    blocked_count += 1
                    blocked_reasons.append(message)
            except Exception as exc:
                failed_count += 1
                safe_message = _safe_error_message(str(exc)) or "반품예정자료 생성 실패"
                error_summary.append(safe_message)
                repo.update_channel_return_candidate(
                    db,
                    candidate,
                    {
                        "return_expected_create_status": RETURN_EXPECTED_FAILED,
                        "return_expected_create_error": safe_message,
                    },
                )
                changed_candidates.append(candidate)

        db.commit()
        return ChannelReturnExpectedBulkCreateResponse(
            total_requested=len(candidates),
            created_count=created_count,
            skipped_duplicate_count=skipped_duplicate_count,
            blocked_count=blocked_count,
            failed_count=failed_count,
            created_candidate_ids=created_candidate_ids,
            blocked_reasons=blocked_reasons[:20],
            error_summary=error_summary[:20],
            candidates=[_candidate_response(candidate) for candidate in changed_candidates],
        ).model_dump()

    def _create_return_expected_from_candidate(self, db: Session, auth: AuthContext, candidate):
        block_reason = self._return_expected_block_reason(candidate)
        if block_reason:
            candidate = repo.update_channel_return_candidate(
                db,
                candidate,
                {
                    "return_expected_create_status": RETURN_EXPECTED_FAILED,
                    "return_expected_create_error": block_reason,
                },
            )
            return candidate, False, False, block_reason

        if candidate.return_expected_id and candidate.return_expected_create_status in {
            RETURN_EXPECTED_CREATED,
            RETURN_EXPECTED_SKIPPED_DUPLICATE,
        }:
            return candidate, False, True, "이미 기존 반품접수 row와 연결되어 있습니다."

        duplicate_candidate = repo.find_created_candidate_by_external_claim(
            db,
            client_id=candidate.client_id,
            external_product_order_id=candidate.external_product_order_id,
            external_claim_id=candidate.external_claim_id,
            exclude_candidate_id=candidate.id,
        )
        if duplicate_candidate is not None and duplicate_candidate.return_expected_id is not None:
            return self._link_duplicate_return_expected(
                db,
                candidate,
                duplicate_candidate.return_expected_id,
                "같은 외부 상품주문/클레임이 이미 반품접수 row와 연결되어 있습니다.",
            )

        duplicate_row = repo.find_return_intake_row_by_tracking_and_product(
            db,
            client_id=candidate.client_id,
            return_tracking_no=candidate.return_tracking_no,
            product_code=candidate.product_code,
        )
        if duplicate_row is not None:
            return self._link_duplicate_return_expected(
                db,
                candidate,
                duplicate_row.id,
                "같은 반품송장/상품코드 반품접수 row가 이미 있어 연결만 처리했습니다.",
            )

        now = datetime.now(timezone.utc)
        batch = return_intake_repository.create_batch(
            db,
            client_id=candidate.client_id,
            client_unit_id=candidate.client_unit_id,
            source_type=RETURN_INTAKE_SOURCE_TYPE_CHANNEL_API,
            source_name=f"{candidate.source_origin} 채널 자동수집",
            status=RETURN_INTAKE_BATCH_STATUS_READY,
            created_by=auth.user_id,
            memo="채널 API 반품 후보에서 생성된 현장 처리 대기 batch입니다.",
        )
        row = ReturnIntakeRow(
            batch_id=batch.id,
            client_id=candidate.client_id,
            client_unit_id=candidate.client_unit_id,
            team_assign_status=RETURN_INTAKE_TEAM_ASSIGNED,
            client_unit_assigned_at=now,
            client_unit_assigned_by=auth.user_id,
            row_no=1,
            order_no=candidate.external_order_id,
            return_tracking_no=candidate.return_tracking_no,
            original_tracking_no=candidate.original_tracking_no,
            product_code=candidate.product_code,
            barcode=candidate.barcode,
            product_name=candidate.product_name,
            option_name=candidate.option_name,
            qty=candidate.qty,
            return_reason=candidate.claim_reason,
            raw_data=self._return_expected_raw_data(candidate),
            validation_status=RETURN_INTAKE_ROW_VALID,
            validation_message=None,
            status=RETURN_INTAKE_ROW_STATUS_READY,
        )
        return_intake_repository.create_rows(db, [row])
        return_intake_repository.update_batch_counts(
            db,
            batch,
            status=RETURN_INTAKE_BATCH_STATUS_READY,
            total_rows=1,
            valid_rows=1,
            warning_rows=0,
            error_rows=0,
        )
        candidate = repo.update_channel_return_candidate(
            db,
            candidate,
            {
                "return_expected_id": row.id,
                "return_expected_created_at": now,
                "return_expected_create_status": RETURN_EXPECTED_CREATED,
                "return_expected_create_error": None,
            },
        )
        return candidate, True, False, "반품처리 화면에서 스캔 조회 가능한 반품접수 row를 생성했습니다."

    def _link_duplicate_return_expected(self, db: Session, candidate, return_expected_id: int, message: str):
        candidate = repo.update_channel_return_candidate(
            db,
            candidate,
            {
                "return_expected_id": return_expected_id,
                "return_expected_created_at": datetime.now(timezone.utc),
                "return_expected_create_status": RETURN_EXPECTED_SKIPPED_DUPLICATE,
                "return_expected_create_error": None,
            },
        )
        return candidate, False, True, message

    def _return_expected_block_reason(self, candidate) -> str | None:
        if candidate.match_status != "READY_FOR_INTAKE":
            return "READY_FOR_INTAKE 상태 후보만 반품예정자료를 생성할 수 있습니다."
        if not candidate.return_tracking_no or candidate.tracking_no_for_scan != candidate.return_tracking_no:
            return "반품 현장 스캔 기준 return_tracking_no가 확정되지 않았습니다."
        if candidate.original_tracking_no and not candidate.return_tracking_no:
            return "원송장만 있는 후보는 반품송장처럼 자동확정할 수 없습니다."
        if candidate.client_unit_id is None:
            return "팀/운영단위가 확정되지 않아 반품예정자료를 생성할 수 없습니다."
        if candidate.product_id is None or not candidate.product_code:
            return "상품마스터가 확정되지 않아 반품예정자료를 생성할 수 없습니다."
        if candidate.qty is None or candidate.qty <= 0:
            return "수량이 1 이상으로 확정되지 않아 반품예정자료를 생성할 수 없습니다."
        return None

    def _return_expected_raw_data(self, candidate) -> dict:
        return {
            "source_type": RETURN_INTAKE_SOURCE_TYPE_CHANNEL_API,
            "source_origin": candidate.source_origin,
            "channel_account_id": candidate.channel_account_id,
            "channel_raw_event_id": candidate.channel_raw_event_id,
            "channel_return_candidate_id": candidate.id,
            "external_order_id": candidate.external_order_id,
            "external_product_order_id": candidate.external_product_order_id,
            "external_claim_id": candidate.external_claim_id,
            "tracking_no_for_scan_source": "return_tracking_no",
            "claim_status": candidate.claim_status,
            "claim_reason": candidate.claim_reason,
            "risk_flags": list(candidate.risk_flags_json or []),
        }

    def _transform_and_save(self, db: Session, *, raw_event, account, reviewed_by: int | None):
        transformer = _transformer_for(raw_event)
        values = transformer.transform(raw_event, account)
        existing = repo.get_channel_return_candidate_by_raw_event(db, raw_event.id)
        if existing is not None:
            values = self._apply_manual_corrections(existing, values)
        values = self._apply_matching_and_status(db, raw_event=raw_event, account=account, values=values)
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
        if existing is not None:
            values.update(
                {
                    "manual_client_unit_id": existing.manual_client_unit_id,
                    "manual_product_id": existing.manual_product_id,
                    "manual_product_code": existing.manual_product_code,
                    "manual_return_tracking_no": existing.manual_return_tracking_no,
                    "manual_original_tracking_no": existing.manual_original_tracking_no,
                    "manual_qty": existing.manual_qty,
                    "manual_review_note": existing.manual_review_note,
                    "manual_reviewed_by": existing.manual_reviewed_by,
                    "manual_reviewed_at": existing.manual_reviewed_at,
                    "correction_status": (
                        "REVIEWED"
                        if existing.correction_status == "REVIEWED"
                        else ("REPROCESS_REQUIRED" if existing.correction_status != "NONE" else "NONE")
                    ),
                    "correction_json": existing.correction_json,
                    "return_expected_create_status": RETURN_EXPECTED_NOT_CREATED,
                    "return_expected_create_error": None,
                }
            )
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

        if values.get("client_unit_id"):
            values["client_unit_id"] = values["client_unit_id"]
        elif account.client_unit_id:
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

    def _apply_manual_corrections(self, candidate, values: dict) -> dict:
        if candidate.manual_client_unit_id is not None:
            values["client_unit_id"] = candidate.manual_client_unit_id
        if candidate.manual_product_id is not None:
            values["product_id"] = candidate.manual_product_id
            values["product_code"] = candidate.manual_product_code or values.get("product_code")
        elif candidate.manual_product_code:
            values["product_code"] = candidate.manual_product_code
        if candidate.manual_return_tracking_no:
            values["return_tracking_no"] = candidate.manual_return_tracking_no
            values["tracking_no_for_scan"] = candidate.manual_return_tracking_no
        elif candidate.manual_original_tracking_no and not values.get("return_tracking_no"):
            values["original_tracking_no"] = candidate.manual_original_tracking_no
            values["tracking_no_for_scan"] = None
        if candidate.manual_original_tracking_no:
            values["original_tracking_no"] = candidate.manual_original_tracking_no
        if candidate.manual_qty is not None:
            values["qty"] = candidate.manual_qty
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
        mapping_product = self._match_product_channel_mapping(db, client_id, values)
        if mapping_product is not None:
            return mapping_product
        return None

    def _match_product_channel_mapping(self, db: Session, client_id: int, values: dict):
        mappings = repo.find_product_channel_mappings(
            db,
            client_id=client_id,
            channel_type=values.get("source_origin") or "",
            external_seller_product_code=_norm_text(values.get("product_code")),
            external_product_name_norm=_norm_text(values.get("product_name")),
            external_option_name_norm=_norm_text(values.get("option_name")),
        )
        product_ids = {mapping.product_id for mapping in mappings}
        if len(product_ids) != 1:
            return None
        mapping = mappings[0]
        product = master_repository.get_product_by_id(db, mapping.product_id)
        if product is None or product.client_id != client_id or not product.active_yn:
            return None
        return product

    def _validate_correction_values(
        self,
        db: Session,
        candidate,
        request: ChannelReturnCandidateCorrectionRequest,
    ) -> dict:
        correction_summary: dict[str, object] = {}
        values: dict[str, object] = {}
        if request.client_unit_id is not None:
            unit = master_repository.get_client_unit_by_id(db, request.client_unit_id)
            if unit is None or unit.client_id != candidate.client_id or not unit.active_yn:
                raise _business_error("CHANNEL_CORRECTION_CLIENT_UNIT_INVALID", "후보 고객사에 속한 사용중 운영단위만 보정할 수 있습니다.")
            values["manual_client_unit_id"] = unit.id
            correction_summary["client_unit_id"] = unit.id

        product = None
        if request.product_id is not None:
            product = master_repository.get_product_by_id(db, request.product_id)
            if product is None or product.client_id != candidate.client_id or not product.active_yn:
                raise _business_error("CHANNEL_CORRECTION_PRODUCT_INVALID", "후보 고객사에 속한 사용중 상품만 보정할 수 있습니다.")
        elif request.product_code:
            product = master_repository.find_product_by_code(db, candidate.client_id, request.product_code)
            if product is None or not product.active_yn:
                raise _business_error("CHANNEL_CORRECTION_PRODUCT_INVALID", "후보 고객사에 속한 사용중 상품만 보정할 수 있습니다.")
        if product is not None:
            values["manual_product_id"] = product.id
            values["manual_product_code"] = product.product_code
            correction_summary["product_id"] = product.id
            correction_summary["product_code"] = product.product_code

        return_tracking_no = _normalize_tracking_no(request.return_tracking_no)
        original_tracking_no = _normalize_tracking_no(request.original_tracking_no)
        if request.return_tracking_no is not None and not return_tracking_no:
            raise _business_error("CHANNEL_CORRECTION_RETURN_TRACKING_INVALID", "반품송장 보정값을 확인하세요.")
        if return_tracking_no:
            values["manual_return_tracking_no"] = return_tracking_no
            correction_summary["return_tracking_no_present"] = True
        elif request.return_tracking_no is not None:
            values["manual_return_tracking_no"] = None
        if original_tracking_no:
            values["manual_original_tracking_no"] = original_tracking_no
            correction_summary["original_tracking_no_present"] = True
        elif request.original_tracking_no is not None:
            values["manual_original_tracking_no"] = None

        if request.qty is not None:
            if request.qty <= 0:
                raise _business_error("CHANNEL_CORRECTION_QTY_INVALID", "수량은 1 이상이어야 합니다.")
            values["manual_qty"] = request.qty
            correction_summary["qty"] = request.qty

        values["manual_review_note"] = _first_text(request.review_note)
        if request.review_note:
            correction_summary["review_note_present"] = True
        values["correction_json"] = correction_summary
        return values

    def _save_product_channel_mapping(self, db: Session, candidate, created_by: int | None) -> None:
        if candidate.manual_product_id is None or not candidate.manual_product_code:
            return
        repo.upsert_product_channel_mapping(
            db,
            client_id=candidate.client_id,
            client_unit_id=candidate.manual_client_unit_id or candidate.client_unit_id,
            channel_type=candidate.source_origin,
            channel_account_id=candidate.channel_account_id,
            external_product_id=candidate.external_product_order_id,
            external_seller_product_code=_norm_text(candidate.product_code),
            external_product_name_norm=_norm_text(candidate.product_name),
            external_option_name_norm=_norm_text(candidate.option_name),
            product_id=candidate.manual_product_id,
            product_code=candidate.manual_product_code,
            decision_type="CORRECTED",
            confidence=100,
            created_from_candidate_id=candidate.id,
            created_by=created_by,
        )

    def _ensure_candidate_not_linked(self, candidate) -> None:
        if candidate.return_expected_id is not None:
            raise _business_error(
                "CHANNEL_CANDIDATE_ALREADY_LINKED",
                "이미 반품접수 row와 연결된 후보는 보정하거나 재처리할 수 없습니다.",
            )

    def _get_scoped_candidate(self, db: Session, auth: AuthContext, *, candidate_id: int):
        candidate = repo.get_channel_return_candidate(db, candidate_id)
        if candidate is None:
            raise _business_error("CHANNEL_RETURN_CANDIDATE_NOT_FOUND", "채널 반품 후보를 찾을 수 없습니다.", 404)
        resolve_effective_client_id(auth, candidate.client_id)
        return candidate


account_service = ChannelAccountService()
sync_service = ChannelSyncService()
transform_service = ChannelCanonicalTransformService()
