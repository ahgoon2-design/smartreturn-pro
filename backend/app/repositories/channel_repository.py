from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.channels import ChannelAccount, ChannelRawEvent, ChannelSyncJob


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
