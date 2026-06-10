from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.auth import Permission, Role, RolePermission, User, UserRole
from app.models.import_job import ImportJob, ImportJobFile
from app.models.master import Agency, Client, ClientWarehouseSetting, Warehouse


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
        Agency.__table__,
        Client.__table__,
        Warehouse.__table__,
        ClientWarehouseSetting.__table__,
        ImportJob.__table__,
        ImportJobFile.__table__,
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


def _create_client(db: Session, code: str = "CLIENT_A", active_yn: bool = True) -> Client:
    agency = Agency(agency_code=f"AGENCY_{code}", agency_name=f"{code} Agency", active_yn=True)
    row = Client(client_code=code, client_name=f"{code} Name", agency_id=None, active_yn=active_yn)
    db.add_all([agency, row])
    db.flush()
    row.agency_id = agency.id
    db.commit()
    return row


def _create_warehouse(db: Session, code: str = "WH_A", active_yn: bool = True) -> Warehouse:
    row = Warehouse(warehouse_code=code, warehouse_name=f"{code} Name", active_yn=active_yn)
    db.add(row)
    db.commit()
    return row


def _link_warehouse(db: Session, client_id: int, warehouse_id: int) -> ClientWarehouseSetting:
    setting = ClientWarehouseSetting(
        agency_id=db.get(Client, client_id).agency_id if db.get(Client, client_id) is not None else None,
        client_id=client_id,
        warehouse_id=warehouse_id,
        usage_type="IMPORT",
        is_default=False,
        active_yn=True,
    )
    db.add(setting)
    db.commit()
    return setting


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


def _payload(**overrides) -> dict:
    payload = {
        "import_type": "PRODUCT_MASTER",
        "source_type": "EXCEL_FILE",
        "source_name": "product import draft",
        "requested_client_id": 1,
        "requested_warehouse_id": None,
        "file_name": "products.xlsx",
        "worksheet_name": "Sheet1",
        "message": "draft create",
        "raw_json": {"template_version": "v1"},
    }
    payload.update(overrides)
    return payload


def _assert_no_sensitive_values(data: dict) -> None:
    text = str(data).lower()
    for value in ("password", "secret", "token", "hash"):
        assert value not in text


def test_import_job_create_requires_auth(client: TestClient):
    response = client.post("/api/import-jobs", json=_payload())

    assert response.status_code == 401
    assert response.json()["result_code"] == "NOT_AUTHENTICATED"


def test_import_view_only_cannot_create_import_job(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_user(
        db_session,
        login_id="import_view_only",
        role_code="INTERNAL_ADMIN",
        permissions=["IMPORT_VIEW"],
    )

    response = client.post(
        "/api/import-jobs",
        json=_payload(requested_client_id=client_row.id),
        headers=_login(client, "import_view_only"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "PERMISSION_DENIED"


def test_import_manage_permission_is_required(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_user(
        db_session,
        login_id="import_manage_missing",
        role_code="INTERNAL_ADMIN",
        permissions=["MASTER_VIEW"],
    )

    response = client.post(
        "/api/import-jobs",
        json=_payload(requested_client_id=client_row.id),
        headers=_login(client, "import_manage_missing"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "PERMISSION_DENIED"


def test_super_admin_can_create_import_job(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    warehouse = _create_warehouse(db_session)
    _link_warehouse(db_session, client_row.id, warehouse.id)
    _create_user(db_session, login_id="super_import", role_code="SUPER_ADMIN")

    response = client.post(
        "/api/import-jobs",
        json=_payload(requested_client_id=client_row.id, requested_warehouse_id=warehouse.id),
        headers=_login(client, "super_import"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result_code"] == "IMPORT_JOB_CREATED"
    assert body["data"]["requested_client_id"] == client_row.id
    assert body["data"]["requested_warehouse_id"] == warehouse.id
    _assert_no_sensitive_values(body)


def test_internal_admin_with_import_manage_can_create_import_job(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_user(
        db_session,
        login_id="import_admin",
        role_code="INTERNAL_ADMIN",
        permissions=["IMPORT_MANAGE"],
    )

    response = client.post(
        "/api/import-jobs",
        json=_payload(requested_client_id=client_row.id, requested_warehouse_id=None),
        headers=_login(client, "import_admin"),
    )

    assert response.status_code == 200
    assert response.json()["result_code"] == "IMPORT_JOB_CREATED"


def test_client_admin_cannot_create_import_job(client: TestClient, db_session: Session):
    own_client = _create_client(db_session, code="CLIENT_OWN")
    other_client = _create_client(db_session, code="CLIENT_OTHER")
    _create_user(
        db_session,
        login_id="client_import_admin",
        role_code="CLIENT_ADMIN",
        permissions=["IMPORT_MANAGE"],
        client_id=own_client.id,
    )

    response = client.post(
        "/api/import-jobs",
        json=_payload(requested_client_id=other_client.id),
        headers=_login(client, "client_import_admin"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "PERMISSION_DENIED"


def test_import_job_create_blocks_invalid_import_type(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_user(
        db_session,
        login_id="invalid_import_type_admin",
        role_code="INTERNAL_ADMIN",
        permissions=["IMPORT_MANAGE"],
    )

    response = client.post(
        "/api/import-jobs",
        json=_payload(requested_client_id=client_row.id, import_type="GOOGLE_RETURN"),
        headers=_login(client, "invalid_import_type_admin"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "IMPORT_JOB_IMPORT_TYPE_INVALID"


def test_import_job_create_blocks_invalid_source_type(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_user(
        db_session,
        login_id="invalid_source_type_admin",
        role_code="INTERNAL_ADMIN",
        permissions=["IMPORT_MANAGE"],
    )

    response = client.post(
        "/api/import-jobs",
        json=_payload(requested_client_id=client_row.id, source_type="FTP_FILE"),
        headers=_login(client, "invalid_source_type_admin"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "IMPORT_JOB_SOURCE_TYPE_INVALID"


def test_import_job_create_requires_requested_client_id(client: TestClient, db_session: Session):
    _create_user(
        db_session,
        login_id="missing_client_admin",
        role_code="INTERNAL_ADMIN",
        permissions=["IMPORT_MANAGE"],
    )

    response = client.post(
        "/api/import-jobs",
        json=_payload(requested_client_id=None),
        headers=_login(client, "missing_client_admin"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "IMPORT_JOB_REQUESTED_CLIENT_REQUIRED"


def test_import_job_create_blocks_inactive_client(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, active_yn=False)
    _create_user(
        db_session,
        login_id="inactive_client_import_admin",
        role_code="INTERNAL_ADMIN",
        permissions=["IMPORT_MANAGE"],
    )

    response = client.post(
        "/api/import-jobs",
        json=_payload(requested_client_id=client_row.id),
        headers=_login(client, "inactive_client_import_admin"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "MASTER_CLIENT_INACTIVE"


def test_import_job_create_blocks_inactive_warehouse(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    warehouse = _create_warehouse(db_session, active_yn=False)
    _create_user(
        db_session,
        login_id="inactive_warehouse_import_admin",
        role_code="INTERNAL_ADMIN",
        permissions=["IMPORT_MANAGE"],
    )

    response = client.post(
        "/api/import-jobs",
        json=_payload(requested_client_id=client_row.id, requested_warehouse_id=warehouse.id),
        headers=_login(client, "inactive_warehouse_import_admin"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "MASTER_WAREHOUSE_INACTIVE"


def test_import_job_create_blocks_warehouse_from_other_client(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, code="CLIENT_IMPORT_SCOPE")
    other_client = _create_client(db_session, code="CLIENT_IMPORT_OTHER")
    warehouse = _create_warehouse(db_session, code="WH_IMPORT_OTHER")
    _link_warehouse(db_session, other_client.id, warehouse.id)
    _create_user(
        db_session,
        login_id="warehouse_scope_import_admin",
        role_code="INTERNAL_ADMIN",
        permissions=["IMPORT_MANAGE"],
    )

    response = client.post(
        "/api/import-jobs",
        json=_payload(requested_client_id=client_row.id, requested_warehouse_id=warehouse.id),
        headers=_login(client, "warehouse_scope_import_admin"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "IMPORT_JOB_WAREHOUSE_SCOPE_INVALID"


def test_import_job_create_initializes_draft_and_zero_counts(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_user(
        db_session,
        login_id="draft_import_admin",
        role_code="INTERNAL_ADMIN",
        permissions=["IMPORT_MANAGE"],
    )

    response = client.post(
        "/api/import-jobs",
        json=_payload(requested_client_id=client_row.id, requested_warehouse_id=None),
        headers=_login(client, "draft_import_admin"),
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "DRAFT"
    assert data["total_rows"] == 0
    assert data["parsed_rows"] == 0
    assert data["valid_rows"] == 0
    assert data["invalid_rows"] == 0
    assert data["inserted_rows"] == 0
    assert data["updated_rows"] == 0
    assert data["skipped_rows"] == 0
    assert data["error_rows"] == 0
    assert data["progress_percent"] == 0
    assert data["started_at"] is None
    assert data["finished_at"] is None
    _assert_no_sensitive_values(response.json())
