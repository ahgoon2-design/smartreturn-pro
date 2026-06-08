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
    source_type: str = "PASTE",
    client_row: Client | None = None,
    created_by: User | None = None,
) -> ImportJob:
    client_row = client_row or _create_client(db)
    created_by = created_by or _create_user(
        db,
        login_id=f"job_owner_{source_type.lower()}",
        role_code="INTERNAL_ADMIN",
        permissions=["IMPORT_VIEW"],
    )
    job = ImportJob(
        import_type="PRODUCT_MASTER",
        source_type=source_type,
        source_name="paste source",
        requested_client_id=client_row.id,
        requested_warehouse_id=None,
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
        file_name=None,
        worksheet_name=None,
        message=None,
        raw_json=None,
        created_by=created_by.id,
    )
    db.add(job)
    db.commit()
    return job


def _paste_payload(**overrides) -> dict:
    payload = {
        "rows": [
            {"raw_json": {"product_code": "P001"}, "normalized_json": {"product_code": "P001"}},
            {"raw_json": {"product_code": "P002"}, "source_row_key": "row-2"},
        ],
        "replace_existing": False,
        "source_name": "manual paste",
        "worksheet_name": "paste",
    }
    payload.update(overrides)
    return payload


def _assert_no_sensitive_values(data: dict) -> None:
    text = str(data).lower()
    for value in ("password", "secret", "token", "hash"):
        assert value not in text


def test_paste_rows_requires_auth(client: TestClient, db_session: Session):
    job = _create_job(db_session)

    response = client.post(f"/api/import-jobs/{job.id}/rows/paste", json=_paste_payload())

    assert response.status_code == 401
    assert response.json()["result_code"] == "NOT_AUTHENTICATED"


def test_import_manage_permission_is_required(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    _create_user(db_session, login_id="paste_view_only", role_code="INTERNAL_ADMIN", permissions=["IMPORT_VIEW"])

    response = client.post(
        f"/api/import-jobs/{job.id}/rows/paste",
        json=_paste_payload(),
        headers=_login(client, "paste_view_only"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "PERMISSION_DENIED"


def test_paste_rows_missing_job_returns_404(client: TestClient, db_session: Session):
    _create_user(db_session, login_id="paste_missing_admin", role_code="INTERNAL_ADMIN", permissions=["IMPORT_MANAGE"])

    response = client.post(
        "/api/import-jobs/999/rows/paste",
        json=_paste_payload(),
        headers=_login(client, "paste_missing_admin"),
    )

    assert response.status_code == 404
    assert response.json()["result_code"] == "IMPORT_JOB_NOT_FOUND"


def test_client_user_cannot_save_rows_for_other_client_job(client: TestClient, db_session: Session):
    own_client = _create_client(db_session, "CLIENT_OWN")
    other_client = _create_client(db_session, "CLIENT_OTHER")
    job = _create_job(db_session, client_row=other_client)
    _create_user(
        db_session,
        login_id="paste_client_admin",
        role_code="CLIENT_ADMIN",
        permissions=["IMPORT_MANAGE"],
        client_id=own_client.id,
    )

    response = client.post(
        f"/api/import-jobs/{job.id}/rows/paste",
        json=_paste_payload(),
        headers=_login(client, "paste_client_admin"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "PERMISSION_DENIED"


def test_excel_file_job_cannot_save_paste_rows(client: TestClient, db_session: Session):
    job = _create_job(db_session, source_type="EXCEL_FILE")
    _create_user(db_session, login_id="paste_excel_admin", role_code="INTERNAL_ADMIN", permissions=["IMPORT_MANAGE"])

    response = client.post(
        f"/api/import-jobs/{job.id}/rows/paste",
        json=_paste_payload(),
        headers=_login(client, "paste_excel_admin"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "IMPORT_JOB_PASTE_SOURCE_TYPE_INVALID"


def test_paste_job_saves_rows_and_auto_assigns_row_numbers(client: TestClient, db_session: Session):
    job = _create_job(db_session, source_type="PASTE")
    _create_user(
        db_session,
        login_id="paste_success_admin",
        role_code="INTERNAL_ADMIN",
        permissions=["IMPORT_MANAGE", "IMPORT_VIEW"],
    )

    response = client.post(
        f"/api/import-jobs/{job.id}/rows/paste",
        json=_paste_payload(),
        headers=_login(client, "paste_success_admin"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result_code"] == "IMPORT_JOB_ROWS_SAVED"
    assert body["data"]["saved_row_count"] == 2
    assert body["data"]["status"] == "READY_TO_VALIDATE"

    rows_response = client.get(
        f"/api/import-jobs/{job.id}/rows",
        headers=_login(client, "paste_success_admin"),
    )
    items = rows_response.json()["data"]["items"]
    assert [item["row_no"] for item in items] == [1, 2]
    assert [item["validation_status"] for item in items] == ["NOT_VALIDATED", "NOT_VALIDATED"]
    assert all(item["validation_message"] is None for item in items)
    assert all(item["target_action"] is None for item in items)
    _assert_no_sensitive_values(body)


def test_manual_job_saves_rows(client: TestClient, db_session: Session):
    job = _create_job(db_session, source_type="MANUAL")
    _create_user(db_session, login_id="manual_paste_admin", role_code="INTERNAL_ADMIN", permissions=["IMPORT_MANAGE"])

    response = client.post(
        f"/api/import-jobs/{job.id}/rows/paste",
        json=_paste_payload(rows=[{"raw_json": {"product_code": "P-MANUAL"}}]),
        headers=_login(client, "manual_paste_admin"),
    )

    assert response.status_code == 200
    assert response.json()["result_code"] == "IMPORT_JOB_ROWS_SAVED"


def test_paste_rows_preserves_given_row_numbers(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    _create_user(
        db_session,
        login_id="row_no_admin",
        role_code="INTERNAL_ADMIN",
        permissions=["IMPORT_MANAGE", "IMPORT_VIEW"],
    )

    response = client.post(
        f"/api/import-jobs/{job.id}/rows/paste",
        json=_paste_payload(
            rows=[
                {"row_no": 20, "raw_json": {"product_code": "P020"}},
                {"row_no": 10, "raw_json": {"product_code": "P010"}},
            ]
        ),
        headers=_login(client, "row_no_admin"),
    )

    assert response.status_code == 200
    rows_response = client.get(f"/api/import-jobs/{job.id}/rows", headers=_login(client, "row_no_admin"))
    assert [item["row_no"] for item in rows_response.json()["data"]["items"]] == [10, 20]


def test_paste_rows_blocks_duplicate_row_no(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    _create_user(db_session, login_id="dup_row_admin", role_code="INTERNAL_ADMIN", permissions=["IMPORT_MANAGE"])

    response = client.post(
        f"/api/import-jobs/{job.id}/rows/paste",
        json=_paste_payload(
            rows=[
                {"row_no": 1, "raw_json": {"row": 1}},
                {"row_no": 1, "raw_json": {"row": 1}},
            ]
        ),
        headers=_login(client, "dup_row_admin"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "IMPORT_JOB_ROW_NO_DUPLICATED"


def test_paste_rows_blocks_row_no_less_than_one(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    _create_user(db_session, login_id="bad_row_no_admin", role_code="INTERNAL_ADMIN", permissions=["IMPORT_MANAGE"])

    response = client.post(
        f"/api/import-jobs/{job.id}/rows/paste",
        json=_paste_payload(rows=[{"row_no": 0, "raw_json": {"row": 0}}]),
        headers=_login(client, "bad_row_no_admin"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "IMPORT_JOB_ROW_NO_INVALID"


def test_paste_rows_blocks_job_with_existing_rows(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    job = _create_job(db_session, client_row=client_row)
    db_session.add(
        ImportJobRow(
            job_id=job.id,
            client_id=client_row.id,
            row_no=1,
            raw_json={"existing": True},
            validation_status="NOT_VALIDATED",
        )
    )
    db_session.commit()
    _create_user(db_session, login_id="existing_rows_admin", role_code="INTERNAL_ADMIN", permissions=["IMPORT_MANAGE"])

    response = client.post(
        f"/api/import-jobs/{job.id}/rows/paste",
        json=_paste_payload(),
        headers=_login(client, "existing_rows_admin"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "IMPORT_JOB_ROWS_ALREADY_EXISTS"


def test_paste_rows_blocks_replace_existing(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    _create_user(db_session, login_id="replace_admin", role_code="INTERNAL_ADMIN", permissions=["IMPORT_MANAGE"])

    response = client.post(
        f"/api/import-jobs/{job.id}/rows/paste",
        json=_paste_payload(replace_existing=True),
        headers=_login(client, "replace_admin"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "IMPORT_JOB_REPLACE_UNSUPPORTED"


def test_paste_rows_updates_job_counts_and_creates_no_validation_errors(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    _create_user(db_session, login_id="counter_admin", role_code="INTERNAL_ADMIN", permissions=["IMPORT_MANAGE"])

    response = client.post(
        f"/api/import-jobs/{job.id}/rows/paste",
        json=_paste_payload(
            rows=[
                {"raw_json": {"product_code": "P001"}},
                {"raw_json": {"product_code": "P002"}},
                {"raw_json": {"product_code": "P003"}},
            ]
        ),
        headers=_login(client, "counter_admin"),
    )

    assert response.status_code == 200
    db_session.refresh(job)
    assert job.status == "READY_TO_VALIDATE"
    assert job.total_rows == 3
    assert job.parsed_rows == 3
    assert job.valid_rows == 0
    assert job.invalid_rows == 0
    assert job.error_rows == 0
    assert job.progress_percent == 0
    assert db_session.query(ImportValidationError).filter(ImportValidationError.job_id == job.id).count() == 0
