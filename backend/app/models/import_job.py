from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ImportJob(Base):
    __tablename__ = "import_jobs"
    __table_args__ = (
        Index("ix_import_jobs_type_created", "import_type", "created_at"),
        Index("ix_import_jobs_status_created", "status", "created_at"),
        Index("ix_import_jobs_requested_client_created", "requested_client_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(255))
    requested_client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"))
    requested_warehouse_id: Mapped[int | None] = mapped_column(ForeignKey("warehouses.id"))
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    parsed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    inserted_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    updated_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    skipped_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    file_name: Mapped[str | None] = mapped_column(String(255))
    worksheet_name: Mapped[str | None] = mapped_column(String(255))
    message: Mapped[str | None] = mapped_column(Text)
    raw_json: Mapped[dict | None] = mapped_column(JSONB)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ImportJobFile(Base):
    __tablename__ = "import_job_files"
    __table_args__ = (
        Index("ix_import_job_files_job_id", "job_id"),
        Index("ix_import_job_files_uploaded_at", "uploaded_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("import_jobs.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_file_name: Mapped[str | None] = mapped_column(String(255))
    relative_path: Mapped[str | None] = mapped_column(String(500))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ImportJobRow(Base):
    __tablename__ = "import_job_rows"
    __table_args__ = (
        UniqueConstraint("job_id", "row_no", name="uq_import_job_rows_job_row_no"),
        Index("ix_import_job_rows_job_row_no", "job_id", "row_no"),
        Index("ix_import_job_rows_job_validation", "job_id", "validation_status"),
        Index("ix_import_job_rows_row_hash", "row_hash"),
        Index("ix_import_job_rows_source_row_key", "source_row_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("import_jobs.id"), nullable=False)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"))
    row_no: Mapped[int] = mapped_column(Integer, nullable=False)
    source_row_key: Mapped[str | None] = mapped_column(String(255))
    row_hash: Mapped[str | None] = mapped_column(String(128))
    raw_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    normalized_json: Mapped[dict | None] = mapped_column(JSONB)
    validation_status: Mapped[str] = mapped_column(String(50), nullable=False)
    validation_message: Mapped[str | None] = mapped_column(Text)
    target_action: Mapped[str | None] = mapped_column(String(50))
    target_table: Mapped[str | None] = mapped_column(String(100))
    target_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ImportValidationError(Base):
    __tablename__ = "import_validation_errors"
    __table_args__ = (
        Index("ix_import_validation_errors_job_id", "job_id"),
        Index("ix_import_validation_errors_row_id", "row_id"),
        Index("ix_import_validation_errors_row_no", "row_no"),
        Index("ix_import_validation_errors_job_severity", "job_id", "severity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("import_jobs.id"), nullable=False)
    row_id: Mapped[int | None] = mapped_column(ForeignKey("import_job_rows.id"))
    row_no: Mapped[int | None] = mapped_column(Integer)
    field_name: Mapped[str | None] = mapped_column(String(100))
    raw_value: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str] = mapped_column(String(80), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ImportMappingProfile(Base):
    __tablename__ = "import_mapping_profiles"
    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "import_type",
            "source_type",
            "profile_name",
            name="uq_import_mapping_profiles_client_type_name",
        ),
        Index("ix_import_mapping_profiles_client_type", "client_id", "import_type", "source_type"),
        Index("ix_import_mapping_profiles_signature", "header_signature"),
        Index("ix_import_mapping_profiles_active", "active_yn"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"))
    import_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    profile_name: Mapped[str] = mapped_column(String(120), nullable=False)
    header_signature: Mapped[str] = mapped_column(String(500), nullable=False)
    mapping_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    active_yn: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ImportMappingDecision(Base):
    __tablename__ = "import_mapping_decisions"
    __table_args__ = (
        Index("ix_import_mapping_decisions_client_type", "client_id", "import_type", "source_type"),
        Index("ix_import_mapping_decisions_header", "normalized_header"),
        Index("ix_import_mapping_decisions_field", "canonical_field"),
        Index("ix_import_mapping_decisions_type", "decision_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"))
    import_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_channel: Mapped[str | None] = mapped_column(String(80))
    original_header: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_header: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_field: Mapped[str | None] = mapped_column(String(100))
    decision_type: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence_before: Mapped[float | None] = mapped_column(Float)
    confidence_after: Mapped[float | None] = mapped_column(Float)
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("import_mapping_profiles.id"))
    header_signature: Mapped[str | None] = mapped_column(String(500))
    file_signature: Mapped[str | None] = mapped_column(String(255))
    sample_value_hash: Mapped[str | None] = mapped_column(String(128))
    source_context_json: Mapped[dict | None] = mapped_column(JSONB)
    confirmed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
