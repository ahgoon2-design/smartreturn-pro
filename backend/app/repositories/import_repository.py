"""Import job repository."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.import_job import ImportJob, ImportJobFile, ImportJobRow, ImportValidationError
from app.models.master import Client, Warehouse


def create_import_job(
    db: Session,
    *,
    import_type: str,
    source_type: str,
    source_name: str | None,
    requested_client_id: int,
    requested_warehouse_id: int | None,
    file_name: str | None,
    worksheet_name: str | None,
    message: str | None,
    raw_json: dict | None,
    created_by: int,
) -> ImportJob:
    job = ImportJob(
        import_type=import_type,
        source_type=source_type,
        source_name=source_name,
        requested_client_id=requested_client_id,
        requested_warehouse_id=requested_warehouse_id,
        status="DRAFT",
        total_rows=0,
        parsed_rows=0,
        valid_rows=0,
        invalid_rows=0,
        inserted_rows=0,
        updated_rows=0,
        skipped_rows=0,
        error_rows=0,
        progress_percent=0,
        file_name=file_name,
        worksheet_name=worksheet_name,
        message=message,
        raw_json=raw_json,
        created_by=created_by,
        started_at=None,
        finished_at=None,
    )
    db.add(job)
    db.flush()
    return job


def _import_job_query(
    db: Session,
    *,
    client_id: int | None = None,
    import_type: str | None = None,
    status: str | None = None,
):
    query = (
        db.query(ImportJob, Client, Warehouse)
        .outerjoin(Client, Client.id == ImportJob.requested_client_id)
        .outerjoin(Warehouse, Warehouse.id == ImportJob.requested_warehouse_id)
    )
    if client_id is not None:
        query = query.filter(ImportJob.requested_client_id == client_id)
    if import_type:
        query = query.filter(ImportJob.import_type == import_type)
    if status:
        query = query.filter(ImportJob.status == status)
    return query


def list_import_jobs(
    db: Session,
    *,
    client_id: int | None = None,
    import_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> list[tuple[ImportJob, Client | None, Warehouse | None]]:
    query = _import_job_query(
        db,
        client_id=client_id,
        import_type=import_type,
        status=status,
    )
    return (
        query.order_by(ImportJob.created_at.desc(), ImportJob.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )


def count_import_jobs(
    db: Session,
    *,
    client_id: int | None = None,
    import_type: str | None = None,
    status: str | None = None,
) -> int:
    return _import_job_query(
        db,
        client_id=client_id,
        import_type=import_type,
        status=status,
    ).count()


def get_import_job(db: Session, job_id: int) -> tuple[ImportJob, Client | None, Warehouse | None] | None:
    return (
        db.query(ImportJob, Client, Warehouse)
        .outerjoin(Client, Client.id == ImportJob.requested_client_id)
        .outerjoin(Warehouse, Warehouse.id == ImportJob.requested_warehouse_id)
        .filter(ImportJob.id == job_id)
        .one_or_none()
    )


def list_import_job_files(db: Session, *, job_id: int) -> list[ImportJobFile]:
    return (
        db.query(ImportJobFile)
        .filter(ImportJobFile.job_id == job_id)
        .order_by(ImportJobFile.uploaded_at.asc(), ImportJobFile.id.asc())
        .all()
    )


def _import_job_rows_query(
    db: Session,
    *,
    job_id: int,
    validation_status: str | None = None,
):
    query = db.query(ImportJobRow).filter(ImportJobRow.job_id == job_id)
    if validation_status:
        query = query.filter(ImportJobRow.validation_status == validation_status)
    return query


def list_import_job_rows(
    db: Session,
    *,
    job_id: int,
    validation_status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> list[ImportJobRow]:
    query = _import_job_rows_query(
        db,
        job_id=job_id,
        validation_status=validation_status,
    )
    return (
        query.order_by(ImportJobRow.row_no.asc(), ImportJobRow.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )


def count_import_job_rows(
    db: Session,
    *,
    job_id: int,
    validation_status: str | None = None,
) -> int:
    return _import_job_rows_query(
        db,
        job_id=job_id,
        validation_status=validation_status,
    ).count()


def _import_validation_errors_query(
    db: Session,
    *,
    job_id: int,
    severity: str | None = None,
    row_no: int | None = None,
):
    query = db.query(ImportValidationError).filter(ImportValidationError.job_id == job_id)
    if severity:
        query = query.filter(ImportValidationError.severity == severity)
    if row_no is not None:
        query = query.filter(ImportValidationError.row_no == row_no)
    return query


def list_import_validation_errors(
    db: Session,
    *,
    job_id: int,
    severity: str | None = None,
    row_no: int | None = None,
    page: int = 1,
    page_size: int = 50,
) -> list[ImportValidationError]:
    query = _import_validation_errors_query(
        db,
        job_id=job_id,
        severity=severity,
        row_no=row_no,
    )
    return (
        query.order_by(ImportValidationError.row_no.asc(), ImportValidationError.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )


def count_import_validation_errors(
    db: Session,
    *,
    job_id: int,
    severity: str | None = None,
    row_no: int | None = None,
) -> int:
    return _import_validation_errors_query(
        db,
        job_id=job_id,
        severity=severity,
        row_no=row_no,
    ).count()
