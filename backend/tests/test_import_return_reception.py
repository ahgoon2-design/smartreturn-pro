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
from app.models.import_job import (
    ImportJob,
    ImportJobFile,
    ImportJobRow,
    ImportMappingDecision,
    ImportMappingProfile,
    ImportValidationError,
)
from app.models.master import Agency, Client, Warehouse
from app.models.returns import ReturnIntakeBatch, ReturnIntakeRow


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
        ImportJob.__table__,
        ImportJobFile.__table__,
        ImportJobRow.__table__,
        ImportValidationError.__table__,
        ImportMappingProfile.__table__,
        ImportMappingDecision.__table__,
        ReturnIntakeBatch.__table__,
        ReturnIntakeRow.__table__,
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


def _create_client(db: Session, code: str) -> Client:
    agency = Agency(agency_code=f"AGENCY_{code}", agency_name=f"{code} Agency", active_yn=True)
    db.add(agency)
    db.flush()
    row = Client(client_code=code, client_name=f"{code} Name", agency_id=agency.id, active_yn=True)
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
    agency_id: int | None = None,
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
        agency_id=agency_id,
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


def _return_reception_payload(**overrides) -> dict:
    payload = {
        "import_type": "RETURN_RECEPTION",
        "source_type": "PASTE",
        "source_name": "portal return reception",
        "requested_client_id": None,
        "requested_warehouse_id": None,
        "file_name": None,
        "worksheet_name": None,
        "message": None,
        "raw_json": {"portal": True},
    }
    payload.update(overrides)
    return payload


def _create_validated_return_reception_job(db: Session, *, client_row: Client, created_by: User) -> ImportJob:
    job = ImportJob(
        agency_id=client_row.agency_id,
        import_type="RETURN_RECEPTION",
        source_type="PASTE",
        source_name="portal return reception",
        requested_client_id=client_row.id,
        requested_warehouse_id=None,
        status="VALIDATED",
        total_rows=1,
        parsed_rows=1,
        valid_rows=1,
        invalid_rows=0,
        inserted_rows=0,
        updated_rows=0,
        skipped_rows=0,
        error_rows=0,
        progress_percent=100,
        raw_json={
            "mapping": {
                "applied_mapping": {"운송장번호": "tracking_no", "상품코드": "product_code"},
                "required_missing_fields": [],
                "blocked_reasons": [],
                "suggestions": [],
                "mapping_review_confirmed": True,
            }
        },
        created_by=created_by.id,
    )
    db.add(job)
    db.flush()
    db.add(
        ImportJobRow(
            agency_id=client_row.agency_id,
            job_id=job.id,
            client_id=client_row.id,
            row_no=7,
            raw_json={"운송장번호": "123456789012", "상품코드": "SKU-1"},
            normalized_json={"tracking_no": "123456789012", "product_code": "SKU-1"},
            validation_status="VALID",
            source_row_key="paste!7",
        )
    )
    db.commit()
    return job


def test_client_user_can_create_return_reception_import_job(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, "CLIENT_PORTAL_CREATE")
    _create_user(
        db_session,
        login_id="portal_import_create",
        role_code="CLIENT_USER",
        permissions=["RETURN_CLIENT_SUBMIT"],
        client_id=client_row.id,
        agency_id=client_row.agency_id,
    )

    response = client.post(
        "/api/import-jobs",
        json=_return_reception_payload(),
        headers=_login(client, "portal_import_create"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result_code"] == "IMPORT_JOB_CREATED"
    assert body["data"]["import_type"] == "RETURN_RECEPTION"
    assert body["data"]["requested_client_id"] == client_row.id


def test_client_user_cannot_create_product_master_import_job(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, "CLIENT_PORTAL_BLOCK")
    _create_user(
        db_session,
        login_id="portal_import_blocked",
        role_code="CLIENT_USER",
        permissions=["RETURN_CLIENT_SUBMIT"],
        client_id=client_row.id,
        agency_id=client_row.agency_id,
    )

    response = client.post(
        "/api/import-jobs",
        json=_return_reception_payload(import_type="PRODUCT_MASTER", requested_client_id=client_row.id),
        headers=_login(client, "portal_import_blocked"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "PERMISSION_DENIED"


def test_client_scope_denied_when_client_user_requests_other_client(client: TestClient, db_session: Session):
    own_client = _create_client(db_session, "CLIENT_PORTAL_OWN")
    other_client = _create_client(db_session, "CLIENT_PORTAL_OTHER")
    _create_user(
        db_session,
        login_id="portal_import_other_client",
        role_code="CLIENT_ADMIN",
        permissions=["RETURN_CLIENT_SUBMIT"],
        client_id=own_client.id,
        agency_id=own_client.agency_id,
    )

    response = client.post(
        "/api/import-jobs",
        json=_return_reception_payload(requested_client_id=other_client.id),
        headers=_login(client, "portal_import_other_client"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "CLIENT_SCOPE_DENIED"


def test_return_reception_paste_validate_preserves_row_no_and_blocks_korean_tracking_text(
    client: TestClient,
    db_session: Session,
):
    client_row = _create_client(db_session, "CLIENT_PORTAL_VALIDATE")
    _create_user(
        db_session,
        login_id="portal_import_validate",
        role_code="CLIENT_USER",
        permissions=["RETURN_CLIENT_SUBMIT"],
        client_id=client_row.id,
        agency_id=client_row.agency_id,
    )
    headers = _login(client, "portal_import_validate")
    create_response = client.post("/api/import-jobs", json=_return_reception_payload(), headers=headers)
    job_id = create_response.json()["data"]["job_id"]

    paste_response = client.post(
        f"/api/import-jobs/{job_id}/rows/paste",
        json={
            "rows": [
                {"row_no": 7, "raw_json": {"운송장번호": "재접수요청", "상품코드": "SKU-1"}},
                {"row_no": 8, "raw_json": {"운송장번호": "123456789012", "상품코드": "SKU-2"}},
            ]
        },
        headers=headers,
    )
    assert paste_response.status_code == 200

    mapping_response = client.put(
        f"/api/import-jobs/{job_id}/mapping",
        json={
            "mapping_json": {"운송장번호": "tracking_no", "상품코드": "product_code"},
            "save_profile": False,
            "profile_name": None,
        },
        headers=headers,
    )
    assert mapping_response.status_code == 200
    validate_response = client.post(f"/api/import-jobs/{job_id}/validate", json={}, headers=headers)

    assert validate_response.status_code == 200
    assert validate_response.json()["data"]["status"] == "HAS_ERRORS"
    rows_response = client.get(f"/api/import-jobs/{job_id}/rows", headers=headers)
    row_nos = [row["row_no"] for row in rows_response.json()["data"]["items"]]
    assert row_nos == [7, 8]
    errors_response = client.get(f"/api/import-jobs/{job_id}/errors", headers=headers)
    error_codes = {item["error_code"] for item in errors_response.json()["data"]["items"]}
    assert "INVALID_TRACKING_NO_VALUE" in error_codes


def test_return_reception_confirm_creates_return_intake_rows_only(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, "CLIENT_PORTAL_CONFIRM")
    user = _create_user(
        db_session,
        login_id="portal_import_confirm",
        role_code="CLIENT_ADMIN",
        permissions=["RETURN_CLIENT_SUBMIT"],
        client_id=client_row.id,
        agency_id=client_row.agency_id,
    )
    job = _create_validated_return_reception_job(db_session, client_row=client_row, created_by=user)

    response = client.post(
        f"/api/import-jobs/{job.id}/confirm",
        headers=_login(client, "portal_import_confirm"),
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "APPLIED"
    assert data["applied_rows"] == 1
    intake_batch = db_session.query(ReturnIntakeBatch).one()
    intake_row = db_session.query(ReturnIntakeRow).one()
    assert intake_batch.source_type == "IMPORT_RETURN_RECEPTION"
    assert intake_row.return_tracking_no == "123456789012"
    assert intake_row.product_code == "SKU-1"
    assert intake_row.inventory_reflected_yn is False
    assert intake_row.raw_data["import_job_id"] == job.id
    import_row = db_session.query(ImportJobRow).one()
    assert import_row.target_table == "return_intake_rows"
    assert import_row.target_id == intake_row.id


def test_return_reception_confirm_blocks_unconfirmed_review_mapping(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, "CLIENT_PORTAL_REVIEW")
    user = _create_user(
        db_session,
        login_id="portal_import_review",
        role_code="CLIENT_USER",
        permissions=["RETURN_CLIENT_SUBMIT"],
        client_id=client_row.id,
        agency_id=client_row.agency_id,
    )
    job = _create_validated_return_reception_job(db_session, client_row=client_row, created_by=user)
    job.raw_json = {
        "mapping": {
            "applied_mapping": {"운송장번호": "tracking_no", "상품코드": "product_code"},
            "required_missing_fields": [],
            "blocked_reasons": [],
            "suggestions": [
                {"source_header": "운송장번호", "target_field": "tracking_no", "decision_level": "NEEDS_REVIEW"}
            ],
            "mapping_review_confirmed": False,
        }
    }
    db_session.commit()

    response = client.post(
        f"/api/import-jobs/{job.id}/confirm",
        headers=_login(client, "portal_import_review"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "IMPORT_JOB_CONFIRM_MAPPING_BLOCKED"


def test_return_reception_confirm_blocks_invalid_rows(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, "CLIENT_PORTAL_INVALID")
    user = _create_user(
        db_session,
        login_id="portal_import_invalid",
        role_code="CLIENT_USER",
        permissions=["RETURN_CLIENT_SUBMIT"],
        client_id=client_row.id,
        agency_id=client_row.agency_id,
    )
    job = _create_validated_return_reception_job(db_session, client_row=client_row, created_by=user)
    job.status = "HAS_ERRORS"
    job.invalid_rows = 1
    job.error_rows = 1
    row = db_session.query(ImportJobRow).filter(ImportJobRow.job_id == job.id).one()
    row.validation_status = "INVALID"
    db_session.commit()

    response = client.post(
        f"/api/import-jobs/{job.id}/confirm",
        headers=_login(client, "portal_import_invalid"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "IMPORT_JOB_CONFIRM_HAS_ERRORS"


def test_return_reception_confirm_blocks_other_client_scope(client: TestClient, db_session: Session):
    owner_client = _create_client(db_session, "CLIENT_PORTAL_OWNER")
    other_client = _create_client(db_session, "CLIENT_PORTAL_DENIED")
    owner = _create_user(
        db_session,
        login_id="portal_import_owner",
        role_code="CLIENT_USER",
        permissions=["RETURN_CLIENT_SUBMIT"],
        client_id=owner_client.id,
        agency_id=owner_client.agency_id,
    )
    _create_user(
        db_session,
        login_id="portal_import_denied",
        role_code="CLIENT_USER",
        permissions=["RETURN_CLIENT_SUBMIT"],
        client_id=other_client.id,
        agency_id=other_client.agency_id,
    )
    job = _create_validated_return_reception_job(db_session, client_row=owner_client, created_by=owner)

    response = client.post(
        f"/api/import-jobs/{job.id}/confirm",
        headers=_login(client, "portal_import_denied"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "CLIENT_SCOPE_DENIED"
