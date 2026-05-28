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
from app.models.import_job import ImportJob, ImportJobFile, ImportJobRow, ImportValidationError
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


def _create_client(db: Session, code: str, active_yn: bool = True) -> Client:
    row = Client(client_code=code, client_name=f"{code} Name", active_yn=active_yn)
    db.add(row)
    db.commit()
    return row


def _create_warehouse(db: Session, code: str, active_yn: bool = True) -> Warehouse:
    row = Warehouse(warehouse_code=code, warehouse_name=f"{code} Name", active_yn=active_yn)
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


def _login(client: TestClient, login_id: str, password: str = TEST_PASSWORD) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"login_id": login_id, "password": password})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_import_data(db: Session) -> dict[str, object]:
    client_a = _create_client(db, "CLIENT_A")
    client_b = _create_client(db, "CLIENT_B")
    warehouse_a = _create_warehouse(db, "WH_A")
    warehouse_b = _create_warehouse(db, "WH_B")

    admin_user = _create_user(db, login_id="import_owner", role_code="INTERNAL_ADMIN", permissions=["IMPORT_VIEW"])

    job_a = ImportJob(
        import_type="PRODUCT_MASTER",
        source_type="EXCEL",
        source_name="product-master.xlsx",
        requested_client_id=client_a.id,
        requested_warehouse_id=warehouse_a.id,
        status="VALIDATED",
        total_rows=3,
        parsed_rows=3,
        valid_rows=2,
        invalid_rows=1,
        inserted_rows=0,
        updated_rows=0,
        skipped_rows=0,
        error_rows=1,
        progress_percent=100,
        file_name="product-master.xlsx",
        worksheet_name="Sheet1",
        message="validated",
        raw_json={"sheet_count": 1},
        created_by=admin_user.id,
    )
    job_b = ImportJob(
        import_type="RETURN_EXPECTED",
        source_type="PASTE",
        source_name="return-paste",
        requested_client_id=client_b.id,
        requested_warehouse_id=warehouse_b.id,
        status="FAILED",
        total_rows=2,
        parsed_rows=2,
        valid_rows=0,
        invalid_rows=2,
        inserted_rows=0,
        updated_rows=0,
        skipped_rows=0,
        error_rows=2,
        progress_percent=100,
        file_name=None,
        worksheet_name=None,
        message="failed",
        raw_json={"source": "paste"},
        created_by=admin_user.id,
    )
    internal_job = ImportJob(
        import_type="INBOUND_EXPECTED",
        source_type="EXCEL",
        source_name="internal-only.xlsx",
        requested_client_id=None,
        requested_warehouse_id=None,
        status="UPLOADED",
        total_rows=1,
        parsed_rows=0,
        valid_rows=0,
        invalid_rows=0,
        inserted_rows=0,
        updated_rows=0,
        skipped_rows=0,
        error_rows=0,
        progress_percent=0,
        file_name="internal-only.xlsx",
        worksheet_name="Sheet1",
        message=None,
        raw_json={"scope": "internal"},
        created_by=admin_user.id,
    )
    db.add_all([job_a, job_b, internal_job])
    db.flush()

    db.add(
        ImportJobFile(
            job_id=job_a.id,
            file_name="product-master.xlsx",
            stored_file_name="stored-product-master.xlsx",
            relative_path="imports/product-master.xlsx",
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            size_bytes=1024,
            uploaded_by=admin_user.id,
        )
    )

    row_30 = ImportJobRow(
        job_id=job_a.id,
        client_id=client_a.id,
        row_no=30,
        source_row_key="R30",
        row_hash="hash30",
        raw_json={"row": 30},
        normalized_json={"product_code": "P30"},
        validation_status="INVALID",
        validation_message="invalid row",
        target_action="ERROR",
        target_table="products",
        target_id=None,
    )
    row_10 = ImportJobRow(
        job_id=job_a.id,
        client_id=client_a.id,
        row_no=10,
        source_row_key="R10",
        row_hash="hash10",
        raw_json={"row": 10},
        normalized_json={"product_code": "P10"},
        validation_status="VALID",
        validation_message=None,
        target_action="INSERT",
        target_table="products",
        target_id=101,
    )
    row_20 = ImportJobRow(
        job_id=job_a.id,
        client_id=client_a.id,
        row_no=20,
        source_row_key="R20",
        row_hash="hash20",
        raw_json={"row": 20},
        normalized_json={"product_code": "P20"},
        validation_status="WARNING",
        validation_message="warning row",
        target_action="UPDATE",
        target_table="products",
        target_id=102,
    )
    db.add_all([row_30, row_10, row_20])
    db.flush()

    db.add_all(
        [
            ImportValidationError(
                job_id=job_a.id,
                row_id=row_30.id,
                row_no=30,
                field_name="product_code",
                raw_value="DUP-30",
                error_code="DUPLICATED",
                error_message="duplicated",
                severity="ERROR",
            ),
            ImportValidationError(
                job_id=job_a.id,
                row_id=row_10.id,
                row_no=10,
                field_name="product_name",
                raw_value="warn",
                error_code="TRIMMED",
                error_message="trimmed",
                severity="WARNING",
            ),
            ImportValidationError(
                job_id=job_a.id,
                row_id=row_10.id,
                row_no=10,
                field_name="barcode",
                raw_value="",
                error_code="MISSING",
                error_message="missing",
                severity="ERROR",
            ),
        ]
    )
    db.commit()
    return {
        "client_a": client_a,
        "client_b": client_b,
        "job_a": job_a,
        "job_b": job_b,
        "internal_job": internal_job,
    }


def _assert_no_sensitive_values(payload: dict) -> None:
    text = str(payload).lower()
    for value in ("password", "secret", "hash_password", "access_token"):
        assert value not in text


def test_import_jobs_requires_auth(client: TestClient):
    response = client.get("/api/import-jobs")
    assert response.status_code == 401
    assert response.json()["result_code"] == "NOT_AUTHENTICATED"


def test_import_jobs_invalid_token_returns_401(client: TestClient):
    response = client.get("/api/import-jobs", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401
    assert response.json()["result_code"] == "INVALID_TOKEN"


def test_internal_admin_can_list_import_jobs(client: TestClient, db_session: Session):
    _seed_import_data(db_session)
    _create_user(db_session, login_id="internal_admin", role_code="INTERNAL_ADMIN", permissions=["IMPORT_VIEW"])

    response = client.get("/api/import-jobs", headers=_login(client, "internal_admin"))

    assert response.status_code == 200
    body = response.json()
    assert body["result_code"] == "IMPORT_JOB_LIST_FOUND"
    assert body["data"]["total_count"] == 3
    assert len(body["data"]["items"]) == 3
    _assert_no_sensitive_values(body)


def test_client_admin_only_sees_own_client_jobs(client: TestClient, db_session: Session):
    seeded = _seed_import_data(db_session)
    client_a = seeded["client_a"]
    _create_user(
        db_session,
        login_id="client_admin",
        role_code="CLIENT_ADMIN",
        permissions=["IMPORT_VIEW"],
        client_id=client_a.id,
    )

    response = client.get("/api/import-jobs", headers=_login(client, "client_admin"))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_count"] == 1
    assert [item["requested_client_id"] for item in data["items"]] == [client_a.id]


def test_client_admin_other_client_query_is_denied(client: TestClient, db_session: Session):
    seeded = _seed_import_data(db_session)
    client_a = seeded["client_a"]
    client_b = seeded["client_b"]
    _create_user(
        db_session,
        login_id="client_admin_denied",
        role_code="CLIENT_ADMIN",
        permissions=["IMPORT_VIEW"],
        client_id=client_a.id,
    )

    response = client.get(
        f"/api/import-jobs?client_id={client_b.id}",
        headers=_login(client, "client_admin_denied"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "CLIENT_SCOPE_DENIED"


def test_import_job_detail_respects_scope(client: TestClient, db_session: Session):
    seeded = _seed_import_data(db_session)
    client_a = seeded["client_a"]
    job_b = seeded["job_b"]
    _create_user(
        db_session,
        login_id="client_admin_scope",
        role_code="CLIENT_ADMIN",
        permissions=["IMPORT_VIEW"],
        client_id=client_a.id,
    )

    response = client.get(
        f"/api/import-jobs/{job_b.id}",
        headers=_login(client, "client_admin_scope"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "CLIENT_SCOPE_DENIED"


def test_import_job_rows_keep_row_no_order(client: TestClient, db_session: Session):
    seeded = _seed_import_data(db_session)
    job_a = seeded["job_a"]
    _create_user(db_session, login_id="rows_admin", role_code="INTERNAL_ADMIN", permissions=["IMPORT_VIEW"])

    response = client.get(
        f"/api/import-jobs/{job_a.id}/rows",
        headers=_login(client, "rows_admin"),
    )

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert [item["row_no"] for item in items] == [10, 20, 30]


def test_import_job_errors_keep_row_no_and_id_order(client: TestClient, db_session: Session):
    seeded = _seed_import_data(db_session)
    job_a = seeded["job_a"]
    _create_user(db_session, login_id="errors_admin", role_code="INTERNAL_ADMIN", permissions=["IMPORT_VIEW"])

    response = client.get(
        f"/api/import-jobs/{job_a.id}/errors",
        headers=_login(client, "errors_admin"),
    )

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert [(item["row_no"], item["error_code"]) for item in items] == [
        (10, "TRIMMED"),
        (10, "MISSING"),
        (30, "DUPLICATED"),
    ]


def test_import_job_list_pagination_and_filters(client: TestClient, db_session: Session):
    _seed_import_data(db_session)
    _create_user(db_session, login_id="filter_admin", role_code="INTERNAL_ADMIN", permissions=["IMPORT_VIEW"])

    response = client.get(
        "/api/import-jobs?import_type=PRODUCT_MASTER&status=VALIDATED&page=1&page_size=1",
        headers=_login(client, "filter_admin"),
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["page"] == 1
    assert data["page_size"] == 1
    assert data["total_count"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["import_type"] == "PRODUCT_MASTER"
    assert data["items"][0]["status"] == "VALIDATED"


def test_import_job_list_empty_result_is_ok(client: TestClient, db_session: Session):
    _seed_import_data(db_session)
    _create_user(db_session, login_id="empty_admin", role_code="INTERNAL_ADMIN", permissions=["IMPORT_VIEW"])

    response = client.get(
        "/api/import-jobs?status=CANCELLED",
        headers=_login(client, "empty_admin"),
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["items"] == []
    assert data["total_count"] == 0


def test_import_job_rows_and_errors_not_found(client: TestClient, db_session: Session):
    _seed_import_data(db_session)
    _create_user(db_session, login_id="missing_admin", role_code="INTERNAL_ADMIN", permissions=["IMPORT_VIEW"])
    headers = _login(client, "missing_admin")

    rows_response = client.get("/api/import-jobs/999/rows", headers=headers)
    errors_response = client.get("/api/import-jobs/999/errors", headers=headers)

    assert rows_response.status_code == 404
    assert rows_response.json()["result_code"] == "IMPORT_JOB_NOT_FOUND"
    assert errors_response.status_code == 404
    assert errors_response.json()["result_code"] == "IMPORT_JOB_NOT_FOUND"


def test_import_view_permission_is_required(client: TestClient, db_session: Session):
    _seed_import_data(db_session)
    _create_user(db_session, login_id="worker_no_import", role_code="INTERNAL_WORKER", permissions=["MASTER_VIEW"])

    response = client.get("/api/import-jobs", headers=_login(client, "worker_no_import"))

    assert response.status_code == 403
    assert response.json()["result_code"] == "PERMISSION_DENIED"
