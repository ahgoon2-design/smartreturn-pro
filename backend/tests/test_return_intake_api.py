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
from app.models.master import Client, Product, ProductBarcode, Warehouse
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
        Client.__table__,
        Warehouse.__table__,
        Product.__table__,
        ProductBarcode.__table__,
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


def _create_client(db: Session, code: str = "CLIENT_A", active_yn: bool = True) -> Client:
    row = Client(client_code=code, client_name=f"{code} Name", active_yn=active_yn)
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


def _return_permissions() -> list[str]:
    return ["RETURN_VIEW", "RETURN_PREPARE"]


def _create_product(db: Session, client_id: int, code: str = "P001", barcode: str = "880001") -> Product:
    product = Product(
        client_id=client_id,
        product_code=code,
        product_name="Test Product",
        barcode=barcode,
        active_yn=True,
    )
    db.add(product)
    db.flush()
    product_barcode = ProductBarcode(
        client_id=client_id,
        product_id=product.id,
        barcode="880002",
        barcode_norm="880002",
        barcode_type="EA",
        unit_qty=1,
        active_yn=True,
    )
    db.add(product_barcode)
    db.commit()
    return product


def _create_batch(client: TestClient, db: Session, login_id: str, client_id: int) -> int:
    response = client.post(
        "/api/returns/intake/batches",
        json={"client_id": client_id, "source_type": "PASTE", "source_name": "seller paste"},
        headers=_login(client, login_id),
    )
    assert response.status_code == 200
    return response.json()["data"]["batch_id"]


def _rows_payload(**overrides) -> dict:
    payload = {
        "rows": [
            {
                "row_no": 3,
                "order_no": "ORDER-001",
                "return_tracking_no": "RTN-001",
                "product_code": "P001",
                "barcode": "880001",
                "product_name": "Test Product",
                "qty": 1,
                "return_reason": "customer return",
                "customer_phone": "010-1111-2222",
            },
            {
                "row_no": 4,
                "order_no": "ORDER-002",
                "return_tracking_no": "RTN-002",
                "barcode": "880002",
                "qty": 2,
            },
        ],
        "replace_existing": False,
    }
    payload.update(overrides)
    return payload


def _assert_no_sensitive_values(data: dict) -> None:
    text = str(data).lower()
    for value in ("password", "secret", "token", "hash", "010-1111-2222"):
        assert value not in text


def test_return_intake_requires_auth(client: TestClient):
    response = client.post("/api/returns/intake/batches", json={"client_id": 1, "source_type": "PASTE"})

    assert response.status_code == 401
    assert response.json()["result_code"] == "NOT_AUTHENTICATED"


def test_internal_admin_can_create_list_and_get_batch(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_user(
        db_session,
        login_id="return_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers = _login(client, "return_admin")

    create_response = client.post(
        "/api/returns/intake/batches",
        json={"client_id": client_row.id, "source_type": "PASTE", "source_name": "seller paste"},
        headers=headers,
    )
    assert create_response.status_code == 200
    batch_id = create_response.json()["data"]["batch_id"]

    list_response = client.get("/api/returns/intake/batches", headers=headers)
    detail_response = client.get(f"/api/returns/intake/batches/{batch_id}", headers=headers)

    assert list_response.status_code == 200
    assert list_response.json()["data"]["items"][0]["batch_id"] == batch_id
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["status"] == "DRAFT"
    _assert_no_sensitive_values(create_response.json())


def test_paste_rows_preserves_original_row_order(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_user(
        db_session,
        login_id="return_paste_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    batch_id = _create_batch(client, db_session, "return_paste_admin", client_row.id)

    response = client.post(
        f"/api/returns/intake/batches/{batch_id}/rows/paste",
        json=_rows_payload(),
        headers=_login(client, "return_paste_admin"),
    )
    rows_response = client.get(
        f"/api/returns/intake/batches/{batch_id}/rows",
        headers=_login(client, "return_paste_admin"),
    )

    assert response.status_code == 200
    assert response.json()["data"]["saved_row_count"] == 2
    assert rows_response.status_code == 200
    rows = rows_response.json()["data"]["items"]
    assert [row["row_no"] for row in rows] == [3, 4]
    assert rows[0]["customer_phone_masked"] == "****2222"
    _assert_no_sensitive_values(rows_response.json())


def test_validate_marks_matching_products_valid(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_validate_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers = _login(client, "return_validate_admin")
    batch_id = _create_batch(client, db_session, "return_validate_admin", client_row.id)
    client.post(f"/api/returns/intake/batches/{batch_id}/rows/paste", json=_rows_payload(), headers=headers)

    response = client.post(f"/api/returns/intake/batches/{batch_id}/validate", headers=headers)
    rows_response = client.get(f"/api/returns/intake/batches/{batch_id}/rows", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "VALIDATED"
    assert data["valid_rows"] == 2
    assert data["warning_rows"] == 0
    assert data["error_rows"] == 0
    assert {row["validation_status"] for row in rows_response.json()["data"]["items"]} == {"VALID"}
    assert {row["status"] for row in rows_response.json()["data"]["items"]} == {"RECEIVED"}


def test_validate_marks_missing_product_as_warning(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_user(
        db_session,
        login_id="return_warning_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers = _login(client, "return_warning_admin")
    batch_id = _create_batch(client, db_session, "return_warning_admin", client_row.id)
    client.post(f"/api/returns/intake/batches/{batch_id}/rows/paste", json=_rows_payload(), headers=headers)

    response = client.post(f"/api/returns/intake/batches/{batch_id}/validate", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "VALIDATED"
    assert data["warning_rows"] == 2
    assert data["error_rows"] == 0


def test_prepare_processing_converts_valid_and_warning_rows_only(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_prepare_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers = _login(client, "return_prepare_admin")
    batch_id = _create_batch(client, db_session, "return_prepare_admin", client_row.id)
    client.post(
        f"/api/returns/intake/batches/{batch_id}/rows/paste",
        json={
            "rows": [
                {
                    "row_no": 1,
                    "order_no": "ORDER-VALID",
                    "return_tracking_no": "RTN-VALID",
                    "product_code": "P001",
                    "qty": 1,
                },
                {
                    "row_no": 2,
                    "order_no": "ORDER-WARNING",
                    "return_tracking_no": "RTN-WARNING",
                    "product_code": "UNKNOWN-PRODUCT",
                    "qty": 1,
                },
                {
                    "row_no": 3,
                    "order_no": "ORDER-INVALID",
                    "return_tracking_no": "RTN-INVALID",
                    "product_code": "P001",
                    "qty": 0,
                },
            ]
        },
        headers=headers,
    )
    validate_response = client.post(f"/api/returns/intake/batches/{batch_id}/validate", headers=headers)

    response = client.post(f"/api/returns/intake/batches/{batch_id}/prepare-processing", headers=headers)
    rows_response = client.get(f"/api/returns/intake/batches/{batch_id}/rows", headers=headers)
    tasks_response = client.get(
        f"/api/returns/processing/tasks?client_id={client_row.id}&batch_id={batch_id}",
        headers=headers,
    )

    assert validate_response.status_code == 200
    assert validate_response.json()["data"]["status"] == "HAS_ERRORS"
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["prepared_rows"] == 2
    assert data["skipped_rows"] == 0
    assert data["invalid_rows"] == 1
    assert data["warning_rows"] == 1
    assert data["status"] == "READY_FOR_PROCESSING"
    rows = {row["row_no"]: row for row in rows_response.json()["data"]["items"]}
    assert rows[1]["status"] == "READY_FOR_PROCESSING"
    assert rows[2]["status"] == "READY_FOR_PROCESSING"
    assert rows[3]["status"] == "RECEIVED"
    assert tasks_response.status_code == 200
    tasks = tasks_response.json()["data"]["items"]
    assert [task["row_no"] for task in tasks] == [2, 1]
    assert all(task["status"] == "READY_FOR_PROCESSING" for task in tasks)
    _assert_no_sensitive_values(tasks_response.json())


def test_prepare_processing_is_idempotent(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_prepare_repeat_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers = _login(client, "return_prepare_repeat_admin")
    batch_id = _create_batch(client, db_session, "return_prepare_repeat_admin", client_row.id)
    client.post(f"/api/returns/intake/batches/{batch_id}/rows/paste", json=_rows_payload(), headers=headers)
    client.post(f"/api/returns/intake/batches/{batch_id}/validate", headers=headers)
    first_response = client.post(f"/api/returns/intake/batches/{batch_id}/prepare-processing", headers=headers)

    second_response = client.post(f"/api/returns/intake/batches/{batch_id}/prepare-processing", headers=headers)

    assert first_response.status_code == 200
    assert first_response.json()["data"]["prepared_rows"] == 2
    assert second_response.status_code == 200
    second_data = second_response.json()["data"]
    assert second_data["prepared_rows"] == 0
    assert second_data["skipped_rows"] == 2
    assert second_data["invalid_rows"] == 0


def test_prepare_processing_blocks_unvalidated_batch(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_user(
        db_session,
        login_id="return_prepare_block_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers = _login(client, "return_prepare_block_admin")
    batch_id = _create_batch(client, db_session, "return_prepare_block_admin", client_row.id)
    client.post(f"/api/returns/intake/batches/{batch_id}/rows/paste", json=_rows_payload(), headers=headers)

    response = client.post(f"/api/returns/intake/batches/{batch_id}/prepare-processing", headers=headers)

    assert response.status_code == 400
    assert response.json()["result_code"] == "RETURN_INTAKE_PREPARE_STATUS_INVALID"


def test_processing_tasks_support_tracking_search(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_task_search_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers = _login(client, "return_task_search_admin")
    batch_id = _create_batch(client, db_session, "return_task_search_admin", client_row.id)
    client.post(f"/api/returns/intake/batches/{batch_id}/rows/paste", json=_rows_payload(), headers=headers)
    client.post(f"/api/returns/intake/batches/{batch_id}/validate", headers=headers)
    client.post(f"/api/returns/intake/batches/{batch_id}/prepare-processing", headers=headers)

    response = client.get("/api/returns/processing/tasks?tracking_no=RTN-002", headers=headers)

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["return_tracking_no"] == "RTN-002"


@pytest.mark.parametrize(
    ("row", "expected_message"),
    [
        ({"row_no": 1, "order_no": "ORDER-001", "product_code": "P001", "qty": 0}, "수량"),
        ({"row_no": 1, "order_no": "ORDER-001", "qty": 1}, "상품코드"),
        ({"row_no": 1, "product_code": "P001", "qty": 1}, "주문번호"),
    ],
)
def test_validate_marks_required_field_errors(
    client: TestClient,
    db_session: Session,
    row: dict,
    expected_message: str,
):
    client_row = _create_client(db_session)
    _create_user(
        db_session,
        login_id=f"return_error_admin_{expected_message}",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers = _login(client, f"return_error_admin_{expected_message}")
    batch_id = _create_batch(client, db_session, f"return_error_admin_{expected_message}", client_row.id)
    client.post(
        f"/api/returns/intake/batches/{batch_id}/rows/paste",
        json={"rows": [row]},
        headers=headers,
    )

    response = client.post(f"/api/returns/intake/batches/{batch_id}/validate", headers=headers)
    rows_response = client.get(f"/api/returns/intake/batches/{batch_id}/rows", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "HAS_ERRORS"
    saved_row = rows_response.json()["data"]["items"][0]
    assert saved_row["validation_status"] == "INVALID"
    assert expected_message in saved_row["validation_message"]


def test_client_user_cannot_access_other_client_batch(client: TestClient, db_session: Session):
    own_client = _create_client(db_session, code="CLIENT_OWN")
    other_client = _create_client(db_session, code="CLIENT_OTHER")
    _create_user(
        db_session,
        login_id="return_internal_owner",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    _create_user(
        db_session,
        login_id="return_client_user",
        role_code="CLIENT_ADMIN",
        permissions=_return_permissions(),
        client_id=own_client.id,
    )
    batch_id = _create_batch(client, db_session, "return_internal_owner", other_client.id)

    response = client.get(
        f"/api/returns/intake/batches/{batch_id}",
        headers=_login(client, "return_client_user"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "CLIENT_SCOPE_DENIED"
