from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.channels import ChannelAccount, ChannelRawEvent, ChannelReturnCandidate, ChannelSyncJob
from app.models.returns import ReturnIntakeRow


def list_channel_accounts(
    db: Session,
    *,
    client_id: int | None = None,
    channel_type: str | None = None,
    include_inactive: bool = False,
) -> list[ChannelAccount]:
    query = db.query(ChannelAccount)
    if client_id is not None:
        query = query.filter(ChannelAccount.client_id == client_id)
    if channel_type:
        query = query.filter(ChannelAccount.channel_type == channel_type)
    if not include_inactive:
        query = query.filter(ChannelAccount.status != "INACTIVE")
    return query.order_by(ChannelAccount.updated_at.desc(), ChannelAccount.id.desc()).all()


def get_channel_account(db: Session, account_id: int) -> ChannelAccount | None:
    return db.query(ChannelAccount).filter(ChannelAccount.id == account_id).one_or_none()


def create_channel_account(db: Session, **values) -> ChannelAccount:
    account = ChannelAccount(**values)
    db.add(account)
    db.flush()
    return account


def update_channel_account(db: Session, account: ChannelAccount, values: dict) -> ChannelAccount:
    for field, value in values.items():
        setattr(account, field, value)
    db.flush()
    return account


def list_channel_sync_jobs(
    db: Session,
    *,
    account_id: int | None = None,
    limit: int = 50,
) -> list[ChannelSyncJob]:
    query = db.query(ChannelSyncJob)
    if account_id is not None:
        query = query.filter(ChannelSyncJob.channel_account_id == account_id)
    return query.order_by(ChannelSyncJob.created_at.desc(), ChannelSyncJob.id.desc()).limit(limit).all()


def create_channel_sync_job(db: Session, **values) -> ChannelSyncJob:
    job = ChannelSyncJob(**values)
    db.add(job)
    db.flush()
    return job


def update_channel_sync_job(db: Session, job: ChannelSyncJob, values: dict) -> ChannelSyncJob:
    for field, value in values.items():
        setattr(job, field, value)
    db.flush()
    return job


def list_channel_raw_events(
    db: Session,
    *,
    client_id: int | None = None,
    account_id: int | None = None,
    process_status: str | None = None,
    limit: int = 100,
) -> list[ChannelRawEvent]:
    query = db.query(ChannelRawEvent).join(ChannelAccount, ChannelAccount.id == ChannelRawEvent.channel_account_id)
    if client_id is not None:
        query = query.filter(ChannelAccount.client_id == client_id)
    if account_id is not None:
        query = query.filter(ChannelRawEvent.channel_account_id == account_id)
    if process_status:
        query = query.filter(ChannelRawEvent.process_status == process_status)
    return query.order_by(ChannelRawEvent.collected_at.desc(), ChannelRawEvent.id.desc()).limit(limit).all()


def get_channel_raw_event(db: Session, event_id: int) -> ChannelRawEvent | None:
    return db.query(ChannelRawEvent).filter(ChannelRawEvent.id == event_id).one_or_none()


def update_channel_raw_event(db: Session, event: ChannelRawEvent, values: dict) -> ChannelRawEvent:
    for field, value in values.items():
        setattr(event, field, value)
    db.flush()
    return event


def upsert_channel_raw_event(db: Session, *, account: ChannelAccount, event: dict) -> tuple[ChannelRawEvent, bool]:
    raw_hash = str(event["raw_hash"])
    external_product_order_id = event.get("external_product_order_id")
    external_claim_id = event.get("external_claim_id")
    query = db.query(ChannelRawEvent).filter(ChannelRawEvent.channel_account_id == account.id)
    existing = query.filter(ChannelRawEvent.raw_hash == raw_hash).one_or_none()
    if existing is None and external_product_order_id and external_claim_id:
        existing = (
            query.filter(
                ChannelRawEvent.external_product_order_id == external_product_order_id,
                ChannelRawEvent.external_claim_id == external_claim_id,
            )
            .order_by(ChannelRawEvent.id.desc())
            .first()
        )
    values = {
        "channel_type": account.channel_type,
        "event_type": event["event_type"],
        "external_order_id": event.get("external_order_id"),
        "external_product_order_id": external_product_order_id,
        "external_claim_id": external_claim_id,
        "external_tracking_no_hash": event.get("external_tracking_no_hash"),
        "last_changed_at": event.get("last_changed_at"),
        "raw_hash": raw_hash,
        "raw_json": event["raw_json"],
        "process_status": event.get("process_status", "RECEIVED"),
        "process_error_code": event.get("process_error_code"),
        "process_error_message": event.get("process_error_message"),
        "collected_at": event.get("collected_at") or datetime.now(timezone.utc),
    }
    if existing is None:
        raw_event = ChannelRawEvent(channel_account_id=account.id, **values)
        db.add(raw_event)
        db.flush()
        return raw_event, True
    for field, value in values.items():
        setattr(existing, field, value)
    db.flush()
    return existing, False


def get_channel_return_candidate(db: Session, candidate_id: int) -> ChannelReturnCandidate | None:
    return db.query(ChannelReturnCandidate).filter(ChannelReturnCandidate.id == candidate_id).one_or_none()


def get_channel_return_candidate_by_raw_event(db: Session, raw_event_id: int) -> ChannelReturnCandidate | None:
    return (
        db.query(ChannelReturnCandidate)
        .filter(ChannelReturnCandidate.channel_raw_event_id == raw_event_id)
        .one_or_none()
    )


def list_channel_return_candidates(
    db: Session,
    *,
    client_id: int | None = None,
    account_id: int | None = None,
    match_status: str | None = None,
    limit: int = 100,
) -> list[ChannelReturnCandidate]:
    query = db.query(ChannelReturnCandidate)
    if client_id is not None:
        query = query.filter(ChannelReturnCandidate.client_id == client_id)
    if account_id is not None:
        query = query.filter(ChannelReturnCandidate.channel_account_id == account_id)
    if match_status:
        query = query.filter(ChannelReturnCandidate.match_status == match_status)
    return query.order_by(ChannelReturnCandidate.updated_at.desc(), ChannelReturnCandidate.id.desc()).limit(limit).all()


def list_ready_candidates_for_return_expected(
    db: Session,
    *,
    account_id: int,
    limit: int = 100,
) -> list[ChannelReturnCandidate]:
    return (
        db.query(ChannelReturnCandidate)
        .filter(
            ChannelReturnCandidate.channel_account_id == account_id,
            ChannelReturnCandidate.match_status == "READY_FOR_INTAKE",
            ChannelReturnCandidate.return_expected_create_status.in_(("NOT_CREATED", "FAILED")),
        )
        .order_by(ChannelReturnCandidate.updated_at.desc(), ChannelReturnCandidate.id.desc())
        .limit(limit)
        .all()
    )


def update_channel_return_candidate(db: Session, candidate: ChannelReturnCandidate, values: dict) -> ChannelReturnCandidate:
    for field, value in values.items():
        setattr(candidate, field, value)
    db.flush()
    return candidate


def find_created_candidate_by_external_claim(
    db: Session,
    *,
    client_id: int,
    external_product_order_id: str | None,
    external_claim_id: str | None,
    exclude_candidate_id: int | None = None,
) -> ChannelReturnCandidate | None:
    if not external_product_order_id or not external_claim_id:
        return None
    query = db.query(ChannelReturnCandidate).filter(
        ChannelReturnCandidate.client_id == client_id,
        ChannelReturnCandidate.external_product_order_id == external_product_order_id,
        ChannelReturnCandidate.external_claim_id == external_claim_id,
        ChannelReturnCandidate.return_expected_id.isnot(None),
    )
    if exclude_candidate_id is not None:
        query = query.filter(ChannelReturnCandidate.id != exclude_candidate_id)
    return query.order_by(ChannelReturnCandidate.id.desc()).first()


def find_return_intake_row_by_tracking_and_product(
    db: Session,
    *,
    client_id: int,
    return_tracking_no: str,
    product_code: str,
) -> ReturnIntakeRow | None:
    return (
        db.query(ReturnIntakeRow)
        .filter(
            ReturnIntakeRow.client_id == client_id,
            ReturnIntakeRow.return_tracking_no == return_tracking_no,
            ReturnIntakeRow.product_code == product_code,
        )
        .order_by(ReturnIntakeRow.id.desc())
        .first()
    )


def find_candidate_conflicts(
    db: Session,
    *,
    client_id: int,
    return_tracking_no: str | None,
    external_product_order_id: str | None,
    external_claim_id: str | None,
    exclude_candidate_id: int | None = None,
) -> list[ChannelReturnCandidate]:
    if not return_tracking_no:
        return []
    query = db.query(ChannelReturnCandidate).filter(
        ChannelReturnCandidate.client_id == client_id,
        ChannelReturnCandidate.return_tracking_no == return_tracking_no,
    )
    if exclude_candidate_id is not None:
        query = query.filter(ChannelReturnCandidate.id != exclude_candidate_id)
    rows = query.all()
    conflicts: list[ChannelReturnCandidate] = []
    for row in rows:
        if (
            external_product_order_id
            and row.external_product_order_id
            and row.external_product_order_id != external_product_order_id
        ):
            conflicts.append(row)
            continue
        if external_claim_id and row.external_claim_id and row.external_claim_id != external_claim_id:
            conflicts.append(row)
    return conflicts


def upsert_channel_return_candidate(db: Session, *, raw_event: ChannelRawEvent, account: ChannelAccount, values: dict) -> tuple[ChannelReturnCandidate, bool]:
    existing = get_channel_return_candidate_by_raw_event(db, raw_event.id)
    if existing is None:
        candidate = ChannelReturnCandidate(
            channel_raw_event_id=raw_event.id,
            channel_account_id=account.id,
            client_id=account.client_id,
            **values,
        )
        db.add(candidate)
        db.flush()
        return candidate, True
    for field, value in values.items():
        setattr(existing, field, value)
    db.flush()
    return existing, False
