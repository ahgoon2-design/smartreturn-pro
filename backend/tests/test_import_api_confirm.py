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
from app.models.master import Client, Product, ProductBarcode, Warehouse


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
        Product.__table__,
        ProductBarcode.__table__,
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


def _admin_headers(client: TestClient, db: Session, login_id: str = "confirm_admin") -> dict[str, str]:
    _create_user(
        db,
        login_id=login_id,
        role_code="INTERNAL_ADMIN",
        permissions=["IMPORT_MANAGE", "IMPORT_VIEW"],
    )
    return _login(client, login_id)


def _create_product(
    db: Session,
    client_id: int,
    *,
    product_code: str = "PROD_EXIST",
    product_name: str = "Existing Product",
    barcode: str | None = None,
) -> Product:
    product = Product(
        client_id=client_id,
        product_code=product_code,
        product_name=product_name,
        barcode=barcode,
        active_yn=True,
    )
    db.add(product)
    db.commit()
    return product


def _create_product_barcode(
    db: Session,
    product: Product,
    *,
    barcode: str = "BC_EXIST",
    barcode_type: str = "EACH",
    unit_qty: int = 1,
) -> ProductBarcode:
    product_barcode = ProductBarcode(
        client_id=product.client_id,
        product_id=product.id,
        barcode=barcode,
        barcode_norm=barcode,
        barcode_type=barcode_type,
        unit_qty=unit_qty,
        active_yn=True,
    )
    db.add(product_barcode)
    db.commit()
    return product_barcode


def _create_job(
    db: Session,
    *,
    import_type: str = "PRODUCT_MASTER",
    source_type: str = "PASTE",
    status: str = "VALIDATED",
    client_row: Client | None = None,
    created_by: User | None = None,
) -> ImportJob:
    client_row = client_row or _create_client(db)
    created_by = created_by or _create_user(
        db,
        login_id=f"confirm_owner_{import_type.lower()}_{source_type.lower()}",
        role_code="INTERNAL_ADMIN",
        permissions=["IMPORT_VIEW"],
    )
    job = ImportJob(
        import_type=import_type,
        source_type=source_type,
        source_name="confirm source",
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
        progress_percent=100 if status == "VALIDATED" else 0,
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
    normalized_json: dict | None = None,
    validation_status: str = "VALID",
) -> ImportJobRow:
    row = ImportJobRow(
        job_id=job.id,
        client_id=job.requested_client_id,
        row_no=row_no,
        raw_json=normalized_json or {},
        normalized_json=normalized_json,
        validation_status=validation_status,
    )
    db.add(row)
    job.total_rows += 1
    job.parsed_rows += 1
    if validation_status in {"VALID", "WARNING"}:
        job.valid_rows += 1
    if validation_status == "INVALID":
        job.invalid_rows += 1
        job.error_rows += 1
    db.commit()
    return row


def _assert_no_sensitive_values(data: dict) -> None:
    text = str(data).lower()
    for value in ("password", "secret", "token", "hash"):
        assert value not in text


def test_confirm_requires_auth(client: TestClient, db_session: Session):
    job = _create_job(db_session)

    response = client.post(f"/api/import-jobs/{job.id}/confirm")

    assert response.status_code == 401
    assert response.json()["result_code"] == "NOT_AUTHENTICATED"


def test_confirm_missing_job_returns_404(client: TestClient, db_session: Session):
    headers = _admin_headers(client, db_session, "confirm_missing_admin")

    response = client.post("/api/import-jobs/999/confirm", headers=headers)

    assert response.status_code == 404
    assert response.json()["result_code"] == "IMPORT_JOB_NOT_FOUND"


@pytest.mark.parametrize("status", ["DRAFT", "READY_TO_VALIDATE"])
def test_confirm_blocks_not_validated_status(client: TestClient, db_session: Session, status: str):
    job = _create_job(db_session, status=status)
    headers = _admin_headers(client, db_session, f"confirm_{status.lower()}_admin")

    response = client.post(f"/api/import-jobs/{job.id}/confirm", headers=headers)

    assert response.status_code == 400
    assert response.json()["result_code"] == "IMPORT_JOB_CONFIRM_STATUS_INVALID"


def test_confirm_blocks_has_errors_job(client: TestClient, db_session: Session):
    job = _create_job(db_session, status="HAS_ERRORS")
    _add_row(
        db_session,
        job,
        normalized_json={"product_code": "", "product_name": "Broken"},
        validation_status="INVALID",
    )
    headers = _admin_headers(client, db_session, "confirm_has_errors_admin")

    response = client.post(f"/api/import-jobs/{job.id}/confirm", headers=headers)

    assert response.status_code == 400
    assert response.json()["result_code"] == "IMPORT_JOB_CONFIRM_HAS_ERRORS"


def test_confirm_product_master_creates_product_and_barcode(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, "CLIENT_PM")
    job = _create_job(db_session, import_type="PRODUCT_MASTER", source_type="PASTE", client_row=client_row)
    _add_row(
        db_session,
        job,
        normalized_json={"product_code": "PM001", "product_name": "Product Master 1", "barcode": "880000000001"},
        validation_status="WARNING",
    )
    headers = _admin_headers(client, db_session, "confirm_pm_admin")

    response = client.post(f"/api/import-jobs/{job.id}/confirm", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["result_code"] == "IMPORT_JOB_CONFIRMED"
    assert data["data"]["status"] == "APPLIED"
    assert data["data"]["applied_rows"] == 1
    product = db_session.query(Product).filter(Product.client_id == client_row.id, Product.product_code == "PM001").one()
    assert product.product_name == "Product Master 1"
    assert db_session.query(ProductBarcode).filter(ProductBarcode.product_id == product.id).count() == 1
    _assert_no_sensitive_values(data)


def test_confirm_excel_file_uses_same_apply_flow(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, "CLIENT_XLSX")
    job = _create_job(db_session, import_type="PRODUCT_MASTER", source_type="EXCEL_FILE", client_row=client_row)
    _add_row(
        db_session,
        job,
        normalized_json={"product_code": "XL001", "product_name": "Excel Product", "barcode": "880000000002"},
        validation_status="VALID",
    )
    headers = _admin_headers(client, db_session, "confirm_excel_admin")

    response = client.post(f"/api/import-jobs/{job.id}/confirm", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "APPLIED"
    assert db_session.query(Product).filter(Product.client_id == client_row.id, Product.product_code == "XL001").count() == 1


def test_confirm_product_master_skips_existing_product_and_barcode(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, "CLIENT_SKIP")
    product = _create_product(db_session, client_row.id, product_code="DUP001", barcode=None)
    _create_product_barcode(db_session, product, barcode="DUPBC")
    job = _create_job(db_session, import_type="PRODUCT_MASTER", client_row=client_row)
    _add_row(
        db_session,
        job,
        normalized_json={"product_code": "DUP001", "product_name": "Changed Name", "barcode": "DUPBC"},
        validation_status="VALID",
    )
    headers = _admin_headers(client, db_session, "confirm_skip_admin")

    response = client.post(f"/api/import-jobs/{job.id}/confirm", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["applied_rows"] == 0
    assert data["skipped_rows"] == 1
    db_session.refresh(product)
    assert product.product_name == "Existing Product"
    assert db_session.query(ProductBarcode).filter(ProductBarcode.product_id == product.id).count() == 1


def test_confirm_product_barcode_creates_barcode_for_existing_product(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, "CLIENT_PB")
    product = _create_product(db_session, client_row.id, product_code="PB001", barcode=None)
    job = _create_job(db_session, import_type="PRODUCT_BARCODE", client_row=client_row)
    _add_row(
        db_session,
        job,
        normalized_json={"product_code": "PB001", "barcode": "288000000001", "barcode_type": "BOX", "unit_qty": "10"},
        validation_status="VALID",
    )
    headers = _admin_headers(client, db_session, "confirm_pb_admin")

    response = client.post(f"/api/import-jobs/{job.id}/confirm", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "APPLIED"
    assert data["applied_rows"] == 1
    product_barcode = db_session.query(ProductBarcode).filter(ProductBarcode.product_id == product.id).one()
    assert product_barcode.barcode == "288000000001"
    assert product_barcode.barcode_type == "BOX"
    assert product_barcode.unit_qty == 10


def test_confirm_product_barcode_missing_product_marks_failed(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, "CLIENT_MISSING_PRODUCT")
    job = _create_job(db_session, import_type="PRODUCT_BARCODE", client_row=client_row)
    _add_row(
        db_session,
        job,
        normalized_json={"product_code": "NO_PRODUCT", "barcode": "299000000001", "barcode_type": "EACH"},
        validation_status="VALID",
    )
    headers = _admin_headers(client, db_session, "confirm_missing_product_admin")

    response = client.post(f"/api/import-jobs/{job.id}/confirm", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["result_code"] == "IMPORT_JOB_CONFIRM_PARTIAL_FAILED"
    assert data["status"] == "FAILED"
    assert data["failed_rows"] == 1
    assert db_session.query(ImportValidationError).filter(ImportValidationError.error_code == "PRODUCT_NOT_FOUND").count() == 1


def test_confirm_blocks_reconfirm_after_applied(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, "CLIENT_RECONFIRM")
    job = _create_job(db_session, import_type="PRODUCT_MASTER", status="APPLIED", client_row=client_row)
    headers = _admin_headers(client, db_session, "confirm_reconfirm_admin")

    response = client.post(f"/api/import-jobs/{job.id}/confirm", headers=headers)

    assert response.status_code == 400
    assert response.json()["result_code"] == "IMPORT_JOB_CONFIRM_ALREADY_DONE"
