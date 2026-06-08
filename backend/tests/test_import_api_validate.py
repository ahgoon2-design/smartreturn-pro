from collections.abc import Generator

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.auth import Permission, Role, RolePermission, User, UserRole
from app.models.import_job import ImportJob, ImportJobFile, ImportJobRow, ImportMappingDecision, ImportMappingProfile, ImportValidationError
from app.models.master import Client, Warehouse


TEST_PASSWORD = "DummyPass123!"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, compiler, **kwargs):
    return compiler.visit_JSON(_type, **kwargs)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        Client.__table__,
        Warehouse.__table__,
        ImportJob.__table__,
        ImportJobFile.__table__,
        ImportJobRow.__table__,
        ImportValidationError.__table__,
        ImportMappingProfile.__table__,
        ImportMappingDecision.__table__,
        Role.__table__,
        Permission.__table__,
        User.__table__,
        UserRole.__table__,
        RolePermission.__table__,
    ):
        table.create(bind=engine)

    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _create_client(db: Session, code: str = "CLIENT_A") -> Client:
    row = Client(client_code=code, client_name=f"{code} Name", active_yn=True)
    db.add(row)
    db.commit()
    return row


def _create_user(
    db: Session,
    *,
    login_id: str,
    role_code: str,
    permissions: list[str] | None = None,
    client_id: int | None = None,
) -> User:
    role_type = "INTERNAL" if role_code in {"SUPER_ADMIN", "INTERNAL_ADMIN", "INTERNAL_WORKER"} else "CLIENT"
    role = db.query(Role).filter(Role.role_code == role_code).one_or_none()
    if role is None:
        role = Role(role_code=role_code, role_name=role_code, role_type=role_type, active_yn=True)
        db.add(role)
        db.flush()

    user = User(
        login_id=login_id,
        user_name=f"{login_id} user",
        password_hash=hash_password(TEST_PASSWORD),
        client_id=client_id,
        active_yn=True,
        must_change_password=False,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))

    for permission_code in permissions or []:
        permission = db.query(Permission).filter(Permission.permission_code == permission_code).one_or_none()
        if permission is None:
            permission = Permission(permission_code=permission_code, permission_name=permission_code, active_yn=True)
            db.add(permission)
            db.flush()
        exists = (
            db.query(RolePermission)
            .filter(RolePermission.role_id == role.id, RolePermission.permission_id == permission.id)
            .one_or_none()
        )
        if exists is None:
            db.add(RolePermission(role_id=role.id, permission_id=permission.id))

    db.commit()
    return user


def _login(client: TestClient, login_id: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"login_id": login_id, "password": TEST_PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_job(
    db: Session,
    *,
    import_type: str = "PRODUCT_MASTER",
    source_type: str = "PASTE",
    status: str = "READY_TO_VALIDATE",
    client_row: Client | None = None,
    created_by: User | None = None,
) -> ImportJob:
    client_row = client_row or _create_client(db)
    created_by = created_by or _create_user(
        db,
        login_id=f"validate_owner_{import_type.lower()}_{source_type.lower()}",
        role_code="INTERNAL_ADMIN",
        permissions=["IMPORT_VIEW"],
    )
    job = ImportJob(
        import_type=import_type,
        source_type=source_type,
        source_name="paste source",
        requested_client_id=client_row.id,
        requested_warehouse_id=None,
        status=status,
        total_rows=0,
        parsed_rows=0,
        valid_rows=0,
        invalid_rows=0,
        inserted_rows=0,
        updated_rows=0,
        skipped_rows=0,
        error_rows=0,
        progress_percent=0,
        file_name=None,
        worksheet_name=None,
        message=None,
        raw_json=None,
        created_by=created_by.id,
    )
    db.add(job)
    db.commit()
    return job


def _add_row(
    db: Session,
    job: ImportJob,
    *,
    row_no: int = 1,
    raw_json: dict | None = None,
    normalized_json: dict | None = None,
    validation_status: str = "NOT_VALIDATED",
) -> ImportJobRow:
    row = ImportJobRow(
        job_id=job.id,
        client_id=job.requested_client_id,
        row_no=row_no,
        raw_json=raw_json or {},
        normalized_json=normalized_json,
        validation_status=validation_status,
    )
    db.add(row)
    job.total_rows += 1
    job.parsed_rows += 1
    db.commit()
    return row


def _admin_headers(client: TestClient, db: Session, login_id: str = "validate_admin") -> dict[str, str]:
    _create_user(
        db,
        login_id=login_id,
        role_code="INTERNAL_ADMIN",
        permissions=["IMPORT_MANAGE", "IMPORT_VIEW"],
    )
    return _login(client, login_id)


def _assert_no_sensitive_values(data: dict) -> None:
    text = str(data).lower()
    for value in ("password", "secret", "token", "hash"):
        assert value not in text


def test_validate_requires_auth(client: TestClient, db_session: Session):
    job = _create_job(db_session)

    response = client.post(f"/api/import-jobs/{job.id}/validate", json={})

    assert response.status_code == 401
    assert response.json()["result_code"] == "NOT_AUTHENTICATED"


def test_import_manage_permission_is_required(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    _create_user(db_session, login_id="validate_view_only", role_code="INTERNAL_ADMIN", permissions=["IMPORT_VIEW"])

    response = client.post(
        f"/api/import-jobs/{job.id}/validate",
        json={},
        headers=_login(client, "validate_view_only"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "PERMISSION_DENIED"


def test_validate_missing_job_returns_404(client: TestClient, db_session: Session):
    headers = _admin_headers(client, db_session, "validate_missing_admin")

    response = client.post("/api/import-jobs/999/validate", json={}, headers=headers)

    assert response.status_code == 404
    assert response.json()["result_code"] == "IMPORT_JOB_NOT_FOUND"


def test_client_user_cannot_validate_other_client_job(client: TestClient, db_session: Session):
    own_client = _create_client(db_session, "CLIENT_OWN")
    other_client = _create_client(db_session, "CLIENT_OTHER")
    job = _create_job(db_session, client_row=other_client)
    _create_user(
        db_session,
        login_id="validate_client_admin",
        role_code="CLIENT_ADMIN",
        permissions=["IMPORT_MANAGE"],
        client_id=own_client.id,
    )

    response = client.post(
        f"/api/import-jobs/{job.id}/validate",
        json={},
        headers=_login(client, "validate_client_admin"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "PERMISSION_DENIED"


def test_validate_blocks_job_not_ready(client: TestClient, db_session: Session):
    job = _create_job(db_session, status="DRAFT")
    _add_row(db_session, job, raw_json={"product_code": "P001", "product_name": "Product", "barcode": "B001"})
    headers = _admin_headers(client, db_session, "validate_status_admin")

    response = client.post(f"/api/import-jobs/{job.id}/validate", json={}, headers=headers)

    assert response.status_code == 400
    assert response.json()["result_code"] == "IMPORT_JOB_VALIDATE_STATUS_INVALID"


def test_validate_blocks_job_without_rows(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    headers = _admin_headers(client, db_session, "validate_no_rows_admin")

    response = client.post(f"/api/import-jobs/{job.id}/validate", json={}, headers=headers)

    assert response.status_code == 400
    assert response.json()["result_code"] == "IMPORT_JOB_VALIDATE_NO_ROWS"


def test_validate_allows_excel_file_source_type_with_saved_rows(client: TestClient, db_session: Session):
    job = _create_job(db_session, source_type="EXCEL_FILE")
    _add_row(db_session, job, raw_json={"product_code": "P001", "product_name": "Product", "barcode": "B001"})
    headers = _admin_headers(client, db_session, "validate_excel_admin")

    response = client.post(f"/api/import-jobs/{job.id}/validate", json={}, headers=headers)

    assert response.status_code == 200
    assert response.json()["result_code"] == "IMPORT_JOB_VALIDATED"
    assert response.json()["data"]["status"] == "VALIDATED"


def test_validate_creates_valid_row(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    _add_row(db_session, job, raw_json={"product_code": "P001", "product_name": "Product", "barcode": "B001"})
    headers = _admin_headers(client, db_session, "validate_valid_admin")

    response = client.post(f"/api/import-jobs/{job.id}/validate", json={}, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["result_code"] == "IMPORT_JOB_VALIDATED"
    assert body["data"]["status"] == "VALIDATED"
    assert body["data"]["valid_rows"] == 1
    assert body["data"]["invalid_rows"] == 0
    assert body["data"]["warning_rows"] == 0
    assert body["data"]["validation_error_count"] == 0
    row = db_session.query(ImportJobRow).filter(ImportJobRow.job_id == job.id).one()
    assert row.validation_status == "VALID"
    assert row.validation_message is None
    _assert_no_sensitive_values(body)


def test_validate_creates_warning_row(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    _add_row(db_session, job, raw_json={"product_code": "P001", "product_name": "Product"})
    headers = _admin_headers(client, db_session, "validate_warning_admin")

    response = client.post(f"/api/import-jobs/{job.id}/validate", json={}, headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "VALIDATED"
    assert data["valid_rows"] == 1
    assert data["warning_rows"] == 1
    assert data["invalid_rows"] == 0
    row = db_session.query(ImportJobRow).filter(ImportJobRow.job_id == job.id).one()
    assert row.validation_status == "WARNING"
    warning = db_session.query(ImportValidationError).filter(ImportValidationError.job_id == job.id).one()
    assert warning.severity == "WARNING"
    assert warning.error_code == "PRODUCT_BARCODE_MISSING"


def test_validate_creates_invalid_row_and_error(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    _add_row(db_session, job, raw_json={"product_code": "P001", "barcode": "B001"})
    headers = _admin_headers(client, db_session, "validate_invalid_admin")

    response = client.post(f"/api/import-jobs/{job.id}/validate", json={}, headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "HAS_ERRORS"
    assert data["valid_rows"] == 0
    assert data["invalid_rows"] == 1
    assert data["error_rows"] == 1
    row = db_session.query(ImportJobRow).filter(ImportJobRow.job_id == job.id).one()
    assert row.validation_status == "INVALID"
    error = db_session.query(ImportValidationError).filter(ImportValidationError.job_id == job.id).one()
    assert error.severity == "ERROR"
    assert error.error_code == "REQUIRED_FIELD_MISSING"


def test_validate_error_and_warning_mixed_row_is_invalid(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    _add_row(db_session, job, raw_json={"product_code": "P001"})
    headers = _admin_headers(client, db_session, "validate_mixed_admin")

    response = client.post(f"/api/import-jobs/{job.id}/validate", json={}, headers=headers)

    assert response.status_code == 200
    row = db_session.query(ImportJobRow).filter(ImportJobRow.job_id == job.id).one()
    assert row.validation_status == "INVALID"
    severities = [
        error.severity
        for error in db_session.query(ImportValidationError)
        .filter(ImportValidationError.job_id == job.id)
        .order_by(ImportValidationError.id.asc())
        .all()
    ]
    assert "ERROR" in severities
    assert "WARNING" in severities


def test_validate_updates_job_status_counts_and_progress(client: TestClient, db_session: Session):
    job = _create_job(db_session, import_type="PRODUCT_BARCODE")
    _add_row(db_session, job, row_no=1, raw_json={"product_code": "P001", "barcode": "B001", "unit_qty": 2})
    _add_row(db_session, job, row_no=2, raw_json={"product_code": "P002", "barcode": "B002", "unit_qty": 0})
    headers = _admin_headers(client, db_session, "validate_counts_admin")

    response = client.post(f"/api/import-jobs/{job.id}/validate", json={}, headers=headers)

    assert response.status_code == 200
    db_session.refresh(job)
    assert job.status == "HAS_ERRORS"
    assert job.valid_rows == 1
    assert job.invalid_rows == 1
    assert job.error_rows == 1
    assert job.progress_percent == 100
    assert job.inserted_rows == 0
    assert job.updated_rows == 0
    assert job.skipped_rows == 0
    assert job.started_at is not None
    assert job.finished_at is not None


def test_validate_blocks_rerun(client: TestClient, db_session: Session):
    job = _create_job(db_session, status="VALIDATED")
    _add_row(
        db_session,
        job,
        raw_json={"product_code": "P001", "product_name": "Product", "barcode": "B001"},
        validation_status="VALID",
    )
    headers = _admin_headers(client, db_session, "validate_rerun_admin")

    response = client.post(f"/api/import-jobs/{job.id}/validate", json={}, headers=headers)

    assert response.status_code == 400
    assert response.json()["result_code"] == "IMPORT_JOB_VALIDATE_ALREADY_DONE"


def test_validate_blocks_force_true(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    _add_row(db_session, job, raw_json={"product_code": "P001", "product_name": "Product", "barcode": "B001"})
    headers = _admin_headers(client, db_session, "validate_force_admin")

    response = client.post(f"/api/import-jobs/{job.id}/validate", json={"force": True}, headers=headers)

    assert response.status_code == 400
    assert response.json()["result_code"] == "IMPORT_JOB_VALIDATE_FORCE_UNSUPPORTED"


def test_validate_errors_api_returns_created_errors(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    _add_row(db_session, job, row_no=20, raw_json={"product_code": "P002"})
    _add_row(db_session, job, row_no=10, raw_json={"product_code": "P001", "product_name": "Product"})
    headers = _admin_headers(client, db_session, "validate_errors_admin")

    response = client.post(f"/api/import-jobs/{job.id}/validate", json={}, headers=headers)
    assert response.status_code == 200

    errors_response = client.get(f"/api/import-jobs/{job.id}/errors", headers=headers)
    assert errors_response.status_code == 200
    errors = errors_response.json()["data"]["items"]
    assert [error["row_no"] for error in errors] == [10, 20, 20]
    assert {error["severity"] for error in errors} == {"ERROR", "WARNING"}


def test_validate_rows_api_returns_changed_statuses(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    _add_row(db_session, job, row_no=1, raw_json={"product_code": "P001", "product_name": "Product", "barcode": "B001"})
    _add_row(db_session, job, row_no=2, raw_json={"product_code": "P002", "product_name": "Product"})
    headers = _admin_headers(client, db_session, "validate_rows_admin")

    response = client.post(f"/api/import-jobs/{job.id}/validate", json={}, headers=headers)
    assert response.status_code == 200

    rows_response = client.get(f"/api/import-jobs/{job.id}/rows", headers=headers)
    assert rows_response.status_code == 200
    rows = rows_response.json()["data"]["items"]
    assert [row["validation_status"] for row in rows] == ["VALID", "WARNING"]


def test_validate_uses_normalized_json_before_raw_json(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    _add_row(
        db_session,
        job,
        raw_json={"product_code": "P001"},
        normalized_json={"product_code": "P001", "product_name": "Product", "barcode": "B001"},
    )
    headers = _admin_headers(client, db_session, "validate_normalized_admin")

    response = client.post(f"/api/import-jobs/{job.id}/validate", json={}, headers=headers)

    assert response.status_code == 200
    row = db_session.query(ImportJobRow).filter(ImportJobRow.job_id == job.id).one()
    assert row.validation_status == "VALID"
