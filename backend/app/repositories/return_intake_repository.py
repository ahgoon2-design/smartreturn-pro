from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.master import Client
from app.models.returns import (
    ReturnExternalOutboundBatch,
    ReturnIntakeBatch,
    ReturnIntakeRow,
    ReturnProcessingAttachment,
)


def create_batch(
    db: Session,
    *,
    agency_id: int | None = None,
    client_id: int,
    source_type: str,
    source_name: str | None,
    status: str,
    created_by: int,
    client_unit_id: int | None = None,
    memo: str | None = None,
) -> ReturnIntakeBatch:
    batch = ReturnIntakeBatch(
        agency_id=agency_id,
        client_id=client_id,
        client_unit_id=client_unit_id,
        source_type=source_type,
        source_name=source_name,
        status=status,
        created_by=created_by,
        memo=memo,
    )
    db.add(batch)
    db.flush()
    return batch


def list_batches(
    db: Session,
    *,
    agency_id: int | None = None,
    client_id: int | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[tuple[ReturnIntakeBatch, Client]], int]:
    query = db.query(ReturnIntakeBatch, Client).join(Client, Client.id == ReturnIntakeBatch.client_id)
    if agency_id is not None:
        query = query.filter(ReturnIntakeBatch.agency_id == agency_id)
    if client_id is not None:
        query = query.filter(ReturnIntakeBatch.client_id == client_id)
    total_count = query.count()
    items = (
        query.order_by(ReturnIntakeBatch.created_at.desc(), ReturnIntakeBatch.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total_count


def get_batch_with_client(db: Session, batch_id: int) -> tuple[ReturnIntakeBatch, Client] | None:
    return (
        db.query(ReturnIntakeBatch, Client)
        .join(Client, Client.id == ReturnIntakeBatch.client_id)
        .filter(ReturnIntakeBatch.id == batch_id)
        .one_or_none()
    )


def get_batch(db: Session, batch_id: int) -> ReturnIntakeBatch | None:
    return db.query(ReturnIntakeBatch).filter(ReturnIntakeBatch.id == batch_id).one_or_none()


def delete_rows_for_batch(db: Session, batch_id: int) -> None:
    db.query(ReturnIntakeRow).filter(ReturnIntakeRow.batch_id == batch_id).delete(synchronize_session=False)
    db.flush()


def count_rows(db: Session, batch_id: int) -> int:
    return db.query(ReturnIntakeRow).filter(ReturnIntakeRow.batch_id == batch_id).count()


def create_rows(db: Session, rows: list[ReturnIntakeRow]) -> list[ReturnIntakeRow]:
    db.add_all(rows)
    db.flush()
    return rows


def create_row(db: Session, row: ReturnIntakeRow) -> ReturnIntakeRow:
    db.add(row)
    db.flush()
    return row


def get_next_row_no_for_batch(db: Session, batch_id: int) -> int:
    max_row_no = db.query(func.max(ReturnIntakeRow.row_no)).filter(ReturnIntakeRow.batch_id == batch_id).scalar()
    return int(max_row_no or 0) + 1


def find_open_manual_processing_row(
    db: Session,
    *,
    client_id: int,
    return_tracking_no: str,
    product_code: str,
) -> ReturnIntakeRow | None:
    return (
        db.query(ReturnIntakeRow)
        .join(ReturnIntakeBatch, ReturnIntakeBatch.id == ReturnIntakeRow.batch_id)
        .filter(
            ReturnIntakeRow.client_id == client_id,
            ReturnIntakeRow.return_tracking_no == return_tracking_no,
            ReturnIntakeRow.product_code == product_code,
            ReturnIntakeRow.status.in_(("READY_FOR_PROCESSING", "PROCESSING")),
            ReturnIntakeBatch.source_type.in_(("NO_DETAIL_MANUAL_INTAKE", "UNKNOWN_TRACKING_MANUAL_INTAKE")),
        )
        .order_by(ReturnIntakeRow.id.desc())
        .first()
    )


def list_rows(
    db: Session,
    *,
    batch_id: int,
    page: int = 1,
    page_size: int = 200,
) -> tuple[list[ReturnIntakeRow], int]:
    query = db.query(ReturnIntakeRow).filter(ReturnIntakeRow.batch_id == batch_id)
    total_count = query.count()
    items = (
        query.order_by(ReturnIntakeRow.row_no, ReturnIntakeRow.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total_count


def update_batch_counts(
    db: Session,
    batch: ReturnIntakeBatch,
    *,
    status: str,
    total_rows: int,
    valid_rows: int,
    warning_rows: int,
    error_rows: int,
) -> ReturnIntakeBatch:
    batch.status = status
    batch.total_rows = total_rows
    batch.valid_rows = valid_rows
    batch.warning_rows = warning_rows
    batch.error_rows = error_rows
    db.flush()
    return batch


def update_row_validation(
    db: Session,
    row: ReturnIntakeRow,
    *,
    validation_status: str,
    validation_message: str | None,
    status: str,
) -> ReturnIntakeRow:
    row.validation_status = validation_status
    row.validation_message = validation_message
    row.status = status
    db.flush()
    return row


def update_batch_status(db: Session, batch: ReturnIntakeBatch, *, status: str) -> ReturnIntakeBatch:
    batch.status = status
    db.flush()
    return batch


def list_rows_for_batch(db: Session, batch_id: int) -> list[ReturnIntakeRow]:
    return (
        db.query(ReturnIntakeRow)
        .filter(ReturnIntakeRow.batch_id == batch_id)
        .order_by(ReturnIntakeRow.row_no, ReturnIntakeRow.id)
        .all()
    )


def list_processing_tasks(
    db: Session,
    *,
    client_id: int | None = None,
    batch_id: int | None = None,
    tracking_no: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[tuple[ReturnIntakeRow, Client]], int]:
    query = db.query(ReturnIntakeRow, Client).join(Client, Client.id == ReturnIntakeRow.client_id)
    if client_id is not None:
        query = query.filter(ReturnIntakeRow.client_id == client_id)
    if batch_id is not None:
        query = query.filter(ReturnIntakeRow.batch_id == batch_id)
    if status:
        query = query.filter(ReturnIntakeRow.status == status)
    if tracking_no:
        pattern = f"%{tracking_no}%"
        query = query.filter(
            (ReturnIntakeRow.return_tracking_no.ilike(pattern))
            | (ReturnIntakeRow.original_tracking_no.ilike(pattern))
            | (ReturnIntakeRow.order_no.ilike(pattern))
        )
    total_count = query.count()
    items = (
        query.order_by(ReturnIntakeRow.created_at.desc(), ReturnIntakeRow.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total_count


def get_processing_task_with_client(db: Session, task_id: int) -> tuple[ReturnIntakeRow, Client] | None:
    return (
        db.query(ReturnIntakeRow, Client)
        .join(Client, Client.id == ReturnIntakeRow.client_id)
        .filter(ReturnIntakeRow.id == task_id)
        .one_or_none()
    )


def list_unit_assignment_pending_rows(
    db: Session,
    *,
    client_id: int | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[tuple[ReturnIntakeRow, Client]], int]:
    query = db.query(ReturnIntakeRow, Client).join(Client, Client.id == ReturnIntakeRow.client_id)
    query = query.filter(
        ReturnIntakeRow.client_unit_id.is_(None),
        ReturnIntakeRow.team_assign_status == "TEAM_ASSIGN_PENDING",
    )
    if client_id is not None:
        query = query.filter(ReturnIntakeRow.client_id == client_id)
    if keyword:
        pattern = f"%{keyword}%"
        query = query.filter(
            or_(
                ReturnIntakeRow.return_tracking_no.ilike(pattern),
                ReturnIntakeRow.original_tracking_no.ilike(pattern),
                ReturnIntakeRow.order_no.ilike(pattern),
                ReturnIntakeRow.product_code.ilike(pattern),
                ReturnIntakeRow.barcode.ilike(pattern),
                ReturnIntakeRow.product_name.ilike(pattern),
            )
        )
    total_count = query.count()
    items = (
        query.order_by(ReturnIntakeRow.created_at.desc(), ReturnIntakeRow.row_no, ReturnIntakeRow.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total_count


def list_closing_candidates(
    db: Session,
    *,
    client_id: int | None = None,
    judgement_status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[tuple[ReturnIntakeRow, Client]], int]:
    query = db.query(ReturnIntakeRow, Client).join(Client, Client.id == ReturnIntakeRow.client_id)
    query = query.filter(
        ReturnIntakeRow.status == "COMPLETED",
        ReturnIntakeRow.judgement_status.isnot(None),
        ReturnIntakeRow.inventory_reflected_yn.is_(False),
    )
    if client_id is not None:
        query = query.filter(ReturnIntakeRow.client_id == client_id)
    if judgement_status:
        query = query.filter(ReturnIntakeRow.judgement_status == judgement_status)
    if date_from is not None:
        query = query.filter(ReturnIntakeRow.judged_at >= date_from)
    if date_to is not None:
        query = query.filter(ReturnIntakeRow.judged_at <= date_to)
    total_count = query.count()
    items = (
        query.order_by(ReturnIntakeRow.judged_at.desc(), ReturnIntakeRow.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total_count


def list_closing_rows_by_ids(
    db: Session,
    *,
    row_ids: list[int],
    client_id: int | None = None,
) -> list[tuple[ReturnIntakeRow, Client]]:
    if not row_ids:
        return []
    query = db.query(ReturnIntakeRow, Client).join(Client, Client.id == ReturnIntakeRow.client_id)
    query = query.filter(ReturnIntakeRow.id.in_(row_ids))
    if client_id is not None:
        query = query.filter(ReturnIntakeRow.client_id == client_id)
    return query.order_by(ReturnIntakeRow.id).all()


def list_external_outbound_candidates(
    db: Session,
    *,
    outbound_judgement_statuses: set[str],
    confirmed_status: str,
    client_id: int | None = None,
    judgement_status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    return_management_no: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[tuple[ReturnIntakeRow, Client]], int]:
    query = db.query(ReturnIntakeRow, Client).join(Client, Client.id == ReturnIntakeRow.client_id)
    query = query.filter(
        ReturnIntakeRow.status == "COMPLETED",
        ReturnIntakeRow.judgement_status.in_(outbound_judgement_statuses),
        ReturnIntakeRow.external_outbound_status != confirmed_status,
        (ReturnIntakeRow.return_management_no.isnot(None)) | (ReturnIntakeRow.return_label_no.isnot(None)),
    )
    if client_id is not None:
        query = query.filter(ReturnIntakeRow.client_id == client_id)
    if judgement_status:
        query = query.filter(ReturnIntakeRow.judgement_status == judgement_status)
    if date_from is not None:
        query = query.filter(ReturnIntakeRow.judged_at >= date_from)
    if date_to is not None:
        query = query.filter(ReturnIntakeRow.judged_at <= date_to)
    if return_management_no:
        pattern = f"%{return_management_no}%"
        query = query.filter(
            (ReturnIntakeRow.return_management_no.ilike(pattern))
            | (ReturnIntakeRow.return_label_no.ilike(pattern))
        )
    total_count = query.count()
    items = (
        query.order_by(ReturnIntakeRow.judged_at.desc(), ReturnIntakeRow.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total_count


def list_external_outbound_rows_by_ids(
    db: Session,
    *,
    row_ids: list[int],
    client_id: int | None = None,
) -> list[tuple[ReturnIntakeRow, Client]]:
    if not row_ids:
        return []
    query = db.query(ReturnIntakeRow, Client).join(Client, Client.id == ReturnIntakeRow.client_id)
    query = query.filter(ReturnIntakeRow.id.in_(row_ids))
    if client_id is not None:
        query = query.filter(ReturnIntakeRow.client_id == client_id)
    return query.order_by(ReturnIntakeRow.id).all()


def create_external_outbound_batch(
    db: Session,
    *,
    client_id: int | None,
    batch_no: str,
    status: str,
    target_type: str,
    total_rows: int,
    confirmed_rows: int,
    created_by: int,
    confirmed_by: int | None,
    confirmed_at: datetime | None,
    memo: str | None = None,
) -> ReturnExternalOutboundBatch:
    batch = ReturnExternalOutboundBatch(
        client_id=client_id,
        batch_no=batch_no,
        status=status,
        target_type=target_type,
        total_rows=total_rows,
        confirmed_rows=confirmed_rows,
        created_by=created_by,
        confirmed_by=confirmed_by,
        confirmed_at=confirmed_at,
        memo=memo,
    )
    db.add(batch)
    db.flush()
    return batch


def list_external_outbound_batches(
    db: Session,
    *,
    client_id: int | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[tuple[ReturnExternalOutboundBatch, Client | None]], int]:
    query = db.query(ReturnExternalOutboundBatch, Client).outerjoin(
        Client,
        Client.id == ReturnExternalOutboundBatch.client_id,
    )
    if client_id is not None:
        query = query.filter(ReturnExternalOutboundBatch.client_id == client_id)
    if status:
        query = query.filter(ReturnExternalOutboundBatch.status == status)
    if date_from is not None:
        query = query.filter(ReturnExternalOutboundBatch.created_at >= date_from)
    if date_to is not None:
        query = query.filter(ReturnExternalOutboundBatch.created_at <= date_to)
    if keyword:
        pattern = f"%{keyword}%"
        query = query.filter(
            or_(
                ReturnExternalOutboundBatch.batch_no.ilike(pattern),
                Client.client_code.ilike(pattern),
                Client.client_name.ilike(pattern),
            )
        )
    total_count = query.count()
    items = (
        query.order_by(ReturnExternalOutboundBatch.created_at.desc(), ReturnExternalOutboundBatch.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total_count


def get_external_outbound_batch_with_client(
    db: Session,
    batch_id: int,
    *,
    client_id: int | None = None,
) -> tuple[ReturnExternalOutboundBatch, Client | None] | None:
    query = db.query(ReturnExternalOutboundBatch, Client).outerjoin(
        Client,
        Client.id == ReturnExternalOutboundBatch.client_id,
    )
    query = query.filter(ReturnExternalOutboundBatch.id == batch_id)
    if client_id is not None:
        query = query.filter(ReturnExternalOutboundBatch.client_id == client_id)
    return query.one_or_none()


def list_external_outbound_batch_rows(
    db: Session,
    *,
    batch_id: int,
    client_id: int | None = None,
) -> list[tuple[ReturnIntakeRow, Client]]:
    query = db.query(ReturnIntakeRow, Client).join(Client, Client.id == ReturnIntakeRow.client_id)
    query = query.filter(ReturnIntakeRow.external_outbound_batch_id == batch_id)
    if client_id is not None:
        query = query.filter(ReturnIntakeRow.client_id == client_id)
    return query.order_by(ReturnIntakeRow.row_no, ReturnIntakeRow.id).all()


def list_hold_candidates(
    db: Session,
    *,
    resolved_status: str,
    client_id: int | None = None,
    hold_status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    return_management_no: str | None = None,
    tracking_no: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[tuple[ReturnIntakeRow, Client]], int]:
    query = db.query(ReturnIntakeRow, Client).join(Client, Client.id == ReturnIntakeRow.client_id)
    query = query.filter(
        ReturnIntakeRow.status == "COMPLETED",
        ReturnIntakeRow.judgement_status == "HOLD",
        ReturnIntakeRow.hold_status != resolved_status,
    )
    if client_id is not None:
        query = query.filter(ReturnIntakeRow.client_id == client_id)
    if hold_status:
        query = query.filter(ReturnIntakeRow.hold_status == hold_status)
    if date_from is not None:
        query = query.filter(ReturnIntakeRow.judged_at >= date_from)
    if date_to is not None:
        query = query.filter(ReturnIntakeRow.judged_at <= date_to)
    if return_management_no:
        pattern = f"%{return_management_no}%"
        query = query.filter(
            (ReturnIntakeRow.return_management_no.ilike(pattern))
            | (ReturnIntakeRow.return_label_no.ilike(pattern))
        )
    if tracking_no:
        pattern = f"%{tracking_no}%"
        query = query.filter(
            (ReturnIntakeRow.return_tracking_no.ilike(pattern))
            | (ReturnIntakeRow.original_tracking_no.ilike(pattern))
            | (ReturnIntakeRow.order_no.ilike(pattern))
        )
    total_count = query.count()
    items = (
        query.order_by(ReturnIntakeRow.judged_at.desc(), ReturnIntakeRow.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total_count


def list_disposal_candidates(
    db: Session,
    *,
    confirmed_status: str,
    client_id: int | None = None,
    disposal_status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    return_management_no: str | None = None,
    tracking_no: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[tuple[ReturnIntakeRow, Client]], int]:
    query = db.query(ReturnIntakeRow, Client).join(Client, Client.id == ReturnIntakeRow.client_id)
    query = query.filter(
        ReturnIntakeRow.status == "COMPLETED",
        ReturnIntakeRow.judgement_status == "DISPOSAL",
        ReturnIntakeRow.disposal_status != confirmed_status,
    )
    if client_id is not None:
        query = query.filter(ReturnIntakeRow.client_id == client_id)
    if disposal_status:
        query = query.filter(ReturnIntakeRow.disposal_status == disposal_status)
    if date_from is not None:
        query = query.filter(ReturnIntakeRow.judged_at >= date_from)
    if date_to is not None:
        query = query.filter(ReturnIntakeRow.judged_at <= date_to)
    if return_management_no:
        pattern = f"%{return_management_no}%"
        query = query.filter(
            (ReturnIntakeRow.return_management_no.ilike(pattern))
            | (ReturnIntakeRow.return_label_no.ilike(pattern))
        )
    if tracking_no:
        pattern = f"%{tracking_no}%"
        query = query.filter(
            (ReturnIntakeRow.return_tracking_no.ilike(pattern))
            | (ReturnIntakeRow.original_tracking_no.ilike(pattern))
            | (ReturnIntakeRow.order_no.ilike(pattern))
        )
    total_count = query.count()
    items = (
        query.order_by(ReturnIntakeRow.judged_at.desc(), ReturnIntakeRow.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total_count


def list_return_history(
    db: Session,
    *,
    client_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    keyword: str | None = None,
    tracking_no: str | None = None,
    return_management_no: str | None = None,
    judgement_status: str | None = None,
    status: str | None = None,
    followup_status: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[tuple[ReturnIntakeRow, Client, int]], int]:
    attachment_counts = (
        db.query(
            ReturnProcessingAttachment.return_intake_row_id.label("row_id"),
            func.count(ReturnProcessingAttachment.id).label("attachment_count"),
        )
        .filter(ReturnProcessingAttachment.active_yn.is_(True))
        .group_by(ReturnProcessingAttachment.return_intake_row_id)
        .subquery()
    )
    query = (
        db.query(
            ReturnIntakeRow,
            Client,
            func.coalesce(attachment_counts.c.attachment_count, 0),
        )
        .join(Client, Client.id == ReturnIntakeRow.client_id)
        .outerjoin(attachment_counts, attachment_counts.c.row_id == ReturnIntakeRow.id)
    )
    if client_id is not None:
        query = query.filter(ReturnIntakeRow.client_id == client_id)
    if date_from is not None:
        query = query.filter(ReturnIntakeRow.created_at >= date_from)
    if date_to is not None:
        query = query.filter(ReturnIntakeRow.created_at <= date_to)
    if keyword:
        pattern = f"%{keyword}%"
        query = query.filter(
            or_(
                ReturnIntakeRow.return_tracking_no.ilike(pattern),
                ReturnIntakeRow.original_tracking_no.ilike(pattern),
                ReturnIntakeRow.order_no.ilike(pattern),
                ReturnIntakeRow.product_code.ilike(pattern),
                ReturnIntakeRow.barcode.ilike(pattern),
                ReturnIntakeRow.product_name.ilike(pattern),
                ReturnIntakeRow.return_management_no.ilike(pattern),
                ReturnIntakeRow.return_label_no.ilike(pattern),
            )
        )
    if tracking_no:
        pattern = f"%{tracking_no}%"
        query = query.filter(
            or_(
                ReturnIntakeRow.return_tracking_no.ilike(pattern),
                ReturnIntakeRow.original_tracking_no.ilike(pattern),
                ReturnIntakeRow.order_no.ilike(pattern),
            )
        )
    if return_management_no:
        pattern = f"%{return_management_no}%"
        query = query.filter(
            or_(
                ReturnIntakeRow.return_management_no.ilike(pattern),
                ReturnIntakeRow.return_label_no.ilike(pattern),
            )
        )
    if judgement_status:
        query = query.filter(ReturnIntakeRow.judgement_status == judgement_status)
    if status:
        query = query.filter(ReturnIntakeRow.status == status)
    if followup_status:
        query = _apply_history_followup_filter(query, followup_status)

    total_count = query.count()
    items = (
        query.order_by(ReturnIntakeRow.updated_at.desc(), ReturnIntakeRow.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total_count


def _apply_history_followup_filter(query, followup_status: str):
    if followup_status == "INVENTORY_REFLECTED":
        return query.filter(ReturnIntakeRow.inventory_reflected_yn.is_(True))
    if followup_status == "EXTERNAL_OUTBOUND_CONFIRMED":
        return query.filter(ReturnIntakeRow.external_outbound_status == "CONFIRMED")
    if followup_status == "EXTERNAL_OUTBOUND_TARGET":
        return query.filter(
            ReturnIntakeRow.judgement_status.in_(("REFURB", "SAMPLE", "MANUFACTURER_RETURN")),
            ReturnIntakeRow.external_outbound_status != "CONFIRMED",
        )
    if followup_status == "READY_TO_REJUDGE":
        return query.filter(ReturnIntakeRow.hold_status == "READY_TO_REJUDGE")
    if followup_status == "HOLD_PENDING":
        return query.filter(
            ReturnIntakeRow.judgement_status == "HOLD",
            ReturnIntakeRow.hold_status != "RESOLVED",
        )
    if followup_status == "DISPOSAL_CONFIRMED":
        return query.filter(ReturnIntakeRow.disposal_status == "DISPOSAL_CONFIRMED")
    if followup_status == "DISPOSAL_TARGET":
        return query.filter(
            ReturnIntakeRow.judgement_status == "DISPOSAL",
            ReturnIntakeRow.disposal_status != "DISPOSAL_CONFIRMED",
        )
    if followup_status == "JUDGED":
        return query.filter(
            ReturnIntakeRow.status == "COMPLETED",
            ReturnIntakeRow.judgement_status.isnot(None),
        )
    if followup_status == "PROCESSING_READY":
        return query.filter(ReturnIntakeRow.status == "READY_FOR_PROCESSING")
    if followup_status == "RECEIVED":
        return query.filter(ReturnIntakeRow.status == "RECEIVED")
    return query


def create_processing_attachment(
    db: Session,
    attachment: ReturnProcessingAttachment,
) -> ReturnProcessingAttachment:
    db.add(attachment)
    db.flush()
    return attachment


def list_processing_attachments(
    db: Session,
    *,
    task_id: int,
    include_inactive: bool = False,
) -> list[ReturnProcessingAttachment]:
    query = db.query(ReturnProcessingAttachment).filter(ReturnProcessingAttachment.return_intake_row_id == task_id)
    if not include_inactive:
        query = query.filter(ReturnProcessingAttachment.active_yn.is_(True))
    return query.order_by(ReturnProcessingAttachment.uploaded_at.desc(), ReturnProcessingAttachment.id.desc()).all()


def get_processing_attachment(
    db: Session,
    *,
    task_id: int,
    attachment_id: int,
) -> ReturnProcessingAttachment | None:
    return (
        db.query(ReturnProcessingAttachment)
        .filter(
            ReturnProcessingAttachment.id == attachment_id,
            ReturnProcessingAttachment.return_intake_row_id == task_id,
        )
        .one_or_none()
    )
