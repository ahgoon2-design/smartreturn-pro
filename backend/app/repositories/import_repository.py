"""Import job repository."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.import_job import (
    ImportJob,
    ImportJobFile,
    ImportJobRow,
    ImportMappingDecision,
    ImportMappingProfile,
    ImportValidationError,
)
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
    agency_id: int | None = None,
) -> ImportJob:
    job = ImportJob(
        agency_id=agency_id,
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


def bulk_create_import_job_rows(
    db: Session,
    *,
    job_id: int,
    client_id: int | None,
    rows: list[dict],
    agency_id: int | None = None,
) -> list[ImportJobRow]:
    row_models = [
        ImportJobRow(
            job_id=job_id,
            agency_id=agency_id,
            client_id=client_id,
            row_no=row["row_no"],
            source_row_key=row.get("source_row_key"),
            row_hash=None,
            raw_json=row["raw_json"],
            normalized_json=row.get("normalized_json"),
            validation_status="NOT_VALIDATED",
            validation_message=None,
            target_action=None,
            target_table=None,
            target_id=None,
        )
        for row in rows
    ]
    db.add_all(row_models)
    db.flush()
    return row_models


def create_import_job_file(
    db: Session,
    *,
    job_id: int,
    file_name: str,
    stored_file_name: str | None,
    relative_path: str | None,
    mime_type: str | None,
    size_bytes: int | None,
    uploaded_by: int,
) -> ImportJobFile:
    file = ImportJobFile(
        job_id=job_id,
        file_name=file_name,
        stored_file_name=stored_file_name,
        relative_path=relative_path,
        mime_type=mime_type,
        size_bytes=size_bytes,
        uploaded_by=uploaded_by,
    )
    db.add(file)
    db.flush()
    return file


def update_import_job_after_rows_saved(
    db: Session,
    *,
    job: ImportJob,
    row_count: int,
    source_name: str | None = None,
    worksheet_name: str | None = None,
) -> ImportJob:
    if source_name is not None:
        job.source_name = source_name
    if worksheet_name is not None:
        job.worksheet_name = worksheet_name
    job.status = "READY_TO_VALIDATE"
    job.total_rows = row_count
    job.parsed_rows = row_count
    job.valid_rows = 0
    job.invalid_rows = 0
    job.inserted_rows = 0
    job.updated_rows = 0
    job.skipped_rows = 0
    job.error_rows = 0
    job.progress_percent = 0
    db.flush()
    return job


def update_import_job_mapping_metadata(db: Session, *, job: ImportJob, raw_json: dict | None) -> ImportJob:
    job.raw_json = raw_json
    db.flush()
    return job


def update_import_job_row_mapping(db: Session, *, row: ImportJobRow, normalized_json: dict | None) -> ImportJobRow:
    row.normalized_json = normalized_json
    row.validation_status = "NOT_VALIDATED"
    row.validation_message = None
    row.target_action = None
    row.target_table = None
    row.target_id = None
    db.flush()
    return row


def list_import_job_rows_for_validation(db: Session, *, job_id: int) -> list[ImportJobRow]:
    return (
        db.query(ImportJobRow)
        .filter(ImportJobRow.job_id == job_id)
        .order_by(ImportJobRow.row_no.asc(), ImportJobRow.id.asc())
        .all()
    )


def bulk_create_import_validation_errors(db: Session, *, errors: list[dict]) -> list[ImportValidationError]:
    error_models = [
        ImportValidationError(
            job_id=error["job_id"],
            row_id=error.get("row_id"),
            row_no=error.get("row_no"),
            field_name=error.get("field_name"),
            raw_value=error.get("raw_value"),
            error_code=error["error_code"],
            error_message=error["error_message"],
            severity=error["severity"],
        )
        for error in errors
    ]
    db.add_all(error_models)
    db.flush()
    return error_models


def delete_import_validation_errors(db: Session, *, job_id: int) -> None:
    db.query(ImportValidationError).filter(ImportValidationError.job_id == job_id).delete(synchronize_session=False)
    db.flush()


def update_import_job_row_validation(
    db: Session,
    *,
    row: ImportJobRow,
    validation_status: str,
    validation_message: str | None,
) -> ImportJobRow:
    db.execute(
        text(
            "UPDATE import_job_rows "
            "SET validation_status = :validation_status, validation_message = :validation_message "
            "WHERE id = :row_id"
        ),
        {
            "validation_status": validation_status,
            "validation_message": validation_message,
            "row_id": row.id,
        },
    )
    row.validation_status = validation_status
    row.validation_message = validation_message
    db.flush()
    return row


def update_import_job_after_validation(
    db: Session,
    *,
    job: ImportJob,
    status: str,
    valid_rows: int,
    invalid_rows: int,
    error_rows: int,
    message: str | None,
) -> ImportJob:
    now = datetime.now(timezone.utc)
    if job.started_at is None:
        job.started_at = now
    job.finished_at = now
    job.status = status
    job.valid_rows = valid_rows
    job.invalid_rows = invalid_rows
    job.error_rows = error_rows
    job.progress_percent = 100
    job.inserted_rows = 0
    job.updated_rows = 0
    job.skipped_rows = 0
    job.message = message
    db.flush()
    return job


def force_import_job_row_validation_statuses(
    db: Session,
    *,
    statuses: list[tuple[int, str, str | None]],
) -> None:
    for row_id, validation_status, validation_message in statuses:
        db.execute(
            text(
                "UPDATE import_job_rows "
                "SET validation_status = :validation_status, validation_message = :validation_message "
                "WHERE id = :row_id"
            ),
            {
                "validation_status": validation_status,
                "validation_message": validation_message,
                "row_id": row_id,
            },
        )
    db.flush()
    db.expire_all()




def update_import_job_after_confirm(
    db: Session,
    *,
    job: ImportJob,
    status: str,
    inserted_rows: int,
    updated_rows: int,
    skipped_rows: int,
    error_rows: int,
    message: str | None,
) -> ImportJob:
    now = datetime.now(timezone.utc)
    if job.started_at is None:
        job.started_at = now
    job.finished_at = now
    job.status = status
    job.inserted_rows = inserted_rows
    job.updated_rows = updated_rows
    job.skipped_rows = skipped_rows
    job.error_rows = error_rows
    job.progress_percent = 100
    job.message = message
    db.flush()
    return job


def has_existing_validation_errors(db: Session, *, job_id: int) -> bool:
    return (
        db.query(ImportValidationError.id)
        .filter(ImportValidationError.job_id == job_id)
        .first()
        is not None
    )


def _import_job_query(
    db: Session,
    *,
    agency_id: int | None = None,
    client_id: int | None = None,
    import_type: str | None = None,
    status: str | None = None,
):
    query = (
        db.query(ImportJob, Client, Warehouse)
        .outerjoin(Client, Client.id == ImportJob.requested_client_id)
        .outerjoin(Warehouse, Warehouse.id == ImportJob.requested_warehouse_id)
    )
    if agency_id is not None:
        query = query.filter(ImportJob.agency_id == agency_id)
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
    agency_id: int | None = None,
    client_id: int | None = None,
    import_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> list[tuple[ImportJob, Client | None, Warehouse | None]]:
    query = _import_job_query(
        db,
        agency_id=agency_id,
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
    agency_id: int | None = None,
    client_id: int | None = None,
    import_type: str | None = None,
    status: str | None = None,
) -> int:
    return _import_job_query(
        db,
        agency_id=agency_id,
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
    query = db.query(ImportJobRow).populate_existing().filter(ImportJobRow.job_id == job_id)
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


def list_import_mapping_profiles(
    db: Session,
    *,
    client_id: int | None = None,
    import_type: str | None = None,
    source_type: str | None = None,
    header_signature: str | None = None,
    active_only: bool = True,
) -> list[ImportMappingProfile]:
    query = db.query(ImportMappingProfile)
    if client_id is not None:
        query = query.filter(ImportMappingProfile.client_id == client_id)
    if import_type:
        query = query.filter(ImportMappingProfile.import_type == import_type)
    if source_type:
        query = query.filter(ImportMappingProfile.source_type == source_type)
    if header_signature:
        query = query.filter(ImportMappingProfile.header_signature == header_signature)
    if active_only:
        query = query.filter(ImportMappingProfile.active_yn.is_(True))
    return query.order_by(ImportMappingProfile.last_used_at.desc().nullslast(), ImportMappingProfile.id.desc()).all()


def find_import_mapping_profile(
    db: Session,
    *,
    client_id: int | None,
    import_type: str,
    source_type: str,
    profile_name: str,
) -> ImportMappingProfile | None:
    return (
        db.query(ImportMappingProfile)
        .filter(
            ImportMappingProfile.client_id == client_id,
            ImportMappingProfile.import_type == import_type,
            ImportMappingProfile.source_type == source_type,
            ImportMappingProfile.profile_name == profile_name,
        )
        .one_or_none()
    )


def create_or_update_import_mapping_profile(
    db: Session,
    *,
    client_id: int | None,
    import_type: str,
    source_type: str,
    profile_name: str,
    header_signature: str,
    mapping_json: dict,
    created_by: int,
) -> ImportMappingProfile:
    profile = find_import_mapping_profile(
        db,
        client_id=client_id,
        import_type=import_type,
        source_type=source_type,
        profile_name=profile_name,
    )
    now = datetime.now(timezone.utc)
    if profile is None:
        profile = ImportMappingProfile(
            client_id=client_id,
            import_type=import_type,
            source_type=source_type,
            profile_name=profile_name,
            header_signature=header_signature,
            mapping_json=mapping_json,
            active_yn=True,
            last_used_at=now,
            created_by=created_by,
        )
        db.add(profile)
    else:
        profile.header_signature = header_signature
        profile.mapping_json = mapping_json
        profile.active_yn = True
        profile.last_used_at = now
    db.flush()
    return profile


def touch_import_mapping_profile(db: Session, *, profile: ImportMappingProfile) -> ImportMappingProfile:
    profile.last_used_at = datetime.now(timezone.utc)
    db.flush()
    return profile


def list_import_mapping_decisions(
    db: Session,
    *,
    client_id: int | None = None,
    import_type: str,
    source_type: str,
    normalized_headers: list[str] | None = None,
) -> list[ImportMappingDecision]:
    query = db.query(ImportMappingDecision).filter(
        ImportMappingDecision.import_type == import_type,
        ImportMappingDecision.source_type == source_type,
    )
    if client_id is not None:
        query = query.filter(
            (ImportMappingDecision.client_id == client_id) | (ImportMappingDecision.client_id.is_(None))
        )
    else:
        query = query.filter(ImportMappingDecision.client_id.is_(None))
    if normalized_headers:
        query = query.filter(ImportMappingDecision.normalized_header.in_(normalized_headers))
    return query.order_by(
        ImportMappingDecision.client_id.desc().nullslast(),
        ImportMappingDecision.confirmed_at.desc().nullslast(),
        ImportMappingDecision.id.desc(),
    ).all()


def create_import_mapping_decisions(
    db: Session,
    *,
    decisions: list[dict],
) -> list[ImportMappingDecision]:
    decision_models: list[ImportMappingDecision] = []
    for decision in decisions:
        existing = (
            db.query(ImportMappingDecision)
            .filter(
                ImportMappingDecision.client_id == decision.get("client_id"),
                ImportMappingDecision.import_type == decision.get("import_type"),
                ImportMappingDecision.source_type == decision.get("source_type"),
                ImportMappingDecision.normalized_header == decision.get("normalized_header"),
                ImportMappingDecision.canonical_field == decision.get("canonical_field"),
                ImportMappingDecision.decision_type == decision.get("decision_type"),
                ImportMappingDecision.header_signature == decision.get("header_signature"),
            )
            .one_or_none()
        )
        if existing is None:
            existing = ImportMappingDecision(**decision)
            db.add(existing)
        else:
            existing.original_header = decision.get("original_header") or existing.original_header
            existing.source_channel = decision.get("source_channel")
            existing.confidence_before = decision.get("confidence_before")
            existing.confidence_after = decision.get("confidence_after")
            existing.profile_id = decision.get("profile_id")
            existing.file_signature = decision.get("file_signature")
            existing.sample_value_hash = decision.get("sample_value_hash")
            existing.source_context_json = decision.get("source_context_json")
            existing.confirmed_by = decision.get("confirmed_by")
            existing.confirmed_at = decision.get("confirmed_at")
        decision_models.append(existing)
    db.flush()
    return decision_models
