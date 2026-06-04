from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.master import Client
from app.models.returns import ReturnIntakeBatch, ReturnIntakeRow, ReturnProcessingAttachment


def create_batch(
    db: Session,
    *,
    client_id: int,
    source_type: str,
    source_name: str | None,
    status: str,
    created_by: int,
    memo: str | None = None,
) -> ReturnIntakeBatch:
    batch = ReturnIntakeBatch(
        client_id=client_id,
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
    client_id: int | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[tuple[ReturnIntakeBatch, Client]], int]:
    query = db.query(ReturnIntakeBatch, Client).join(Client, Client.id == ReturnIntakeBatch.client_id)
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
