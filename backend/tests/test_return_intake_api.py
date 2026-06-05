from collections.abc import Generator
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

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
from app.models.inventory import CurrentInventory, InventoryEvent
from app.models.master import Client, ClientWarehouseSetting, Product, ProductBarcode, Warehouse
from app.models.returns import ReturnIntakeBatch, ReturnIntakeRow, ReturnProcessingAttachment
from app.services import return_intake_service


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
        Role.__table__,
        Permission.__table__,
        User.__table__,
        UserRole.__table__,
        RolePermission.__table__,
        ClientWarehouseSetting.__table__,
        InventoryEvent.__table__,
        CurrentInventory.__table__,
        ReturnIntakeBatch.__table__,
        ReturnIntakeRow.__table__,
        ReturnProcessingAttachment.__table__,
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


@pytest.fixture()
def upload_root(monkeypatch: pytest.MonkeyPatch) -> Generator[Path, None, None]:
    root = Path(__file__).resolve().parents[1] / "tmp" / f"return-attachments-{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(return_intake_service, "RETURN_PROCESSING_UPLOAD_ROOT", root)
    try:
        yield root
    finally:
        rmtree(root, ignore_errors=True)


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


def _create_warehouse_setting(
    db: Session,
    *,
    client_id: int,
    usage_type: str = "RETURN_GOOD",
) -> Warehouse:
    warehouse = Warehouse(
        warehouse_code=f"WH-{usage_type}",
        warehouse_name=f"{usage_type} Warehouse",
        warehouse_type="RETURN",
        active_yn=True,
    )
    db.add(warehouse)
    db.flush()
    db.add(
        ClientWarehouseSetting(
            client_id=client_id,
            warehouse_id=warehouse.id,
            usage_type=usage_type,
            is_default=True,
            active_yn=True,
        )
    )
    db.commit()
    return warehouse


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


def _prepare_processing_task(
    client: TestClient,
    db: Session,
    *,
    login_id: str,
    client_id: int,
    rows_payload: dict | None = None,
) -> tuple[dict[str, str], int, int]:
    headers = _login(client, login_id)
    batch_id = _create_batch(client, db, login_id, client_id)
    client.post(
        f"/api/returns/intake/batches/{batch_id}/rows/paste",
        json=rows_payload or _rows_payload(),
        headers=headers,
    )
    client.post(f"/api/returns/intake/batches/{batch_id}/validate", headers=headers)
    client.post(f"/api/returns/intake/batches/{batch_id}/prepare-processing", headers=headers)
    tasks_response = client.get(f"/api/returns/processing/tasks?batch_id={batch_id}", headers=headers)
    assert tasks_response.status_code == 200
    task_id = tasks_response.json()["data"]["items"][0]["task_id"]
    return headers, batch_id, task_id


def _judge_processing_task(
    client: TestClient,
    *,
    task_id: int,
    headers: dict[str, str],
    judgement_status: str = "GOOD",
) -> dict:
    response = client.post(
        f"/api/returns/processing/tasks/{task_id}/judge",
        json={"judgement_status": judgement_status},
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["data"]


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


def test_judge_good_completes_task_without_label(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_judge_good_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers = _login(client, "return_judge_good_admin")
    batch_id = _create_batch(client, db_session, "return_judge_good_admin", client_row.id)
    client.post(f"/api/returns/intake/batches/{batch_id}/rows/paste", json=_rows_payload(), headers=headers)
    client.post(f"/api/returns/intake/batches/{batch_id}/validate", headers=headers)
    client.post(f"/api/returns/intake/batches/{batch_id}/prepare-processing", headers=headers)
    tasks_response = client.get(f"/api/returns/processing/tasks?batch_id={batch_id}", headers=headers)
    task_id = tasks_response.json()["data"]["items"][0]["task_id"]

    response = client.post(
        f"/api/returns/processing/tasks/{task_id}/judge",
        json={"judgement_status": "GOOD", "judgement_memo": "normal return"},
        headers=headers,
    )
    completed_response = client.get(
        f"/api/returns/processing/tasks?batch_id={batch_id}&status=COMPLETED",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "COMPLETED"
    assert data["judgement_status"] == "GOOD"
    assert data["judgement_memo"] == "normal return"
    assert data["label_print_required"] is False
    assert data["label_print_status"] == "NOT_REQUIRED"
    assert data["return_label_no"] is None
    assert data["return_management_no"] is None
    assert data["judged_at"] is not None
    assert data["judged_by"] is not None
    completed_items = completed_response.json()["data"]["items"]
    assert completed_items[0]["judgement_status"] == "GOOD"
    assert completed_items[0]["label_print_required"] is False
    _assert_no_sensitive_values(response.json())


def test_judge_refurb_generates_label_number_and_keeps_save_when_agent_missing(
    client: TestClient,
    db_session: Session,
):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_judge_refurb_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers = _login(client, "return_judge_refurb_admin")
    batch_id = _create_batch(client, db_session, "return_judge_refurb_admin", client_row.id)
    client.post(f"/api/returns/intake/batches/{batch_id}/rows/paste", json=_rows_payload(), headers=headers)
    client.post(f"/api/returns/intake/batches/{batch_id}/validate", headers=headers)
    client.post(f"/api/returns/intake/batches/{batch_id}/prepare-processing", headers=headers)
    tasks_response = client.get(f"/api/returns/processing/tasks?batch_id={batch_id}", headers=headers)
    task_id = tasks_response.json()["data"]["items"][0]["task_id"]

    response = client.post(
        f"/api/returns/processing/tasks/{task_id}/judge",
        json={"judgement_status": "REFURB", "judgement_memo": "needs refurb"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "COMPLETED"
    assert data["judgement_status"] == "REFURB"
    assert data["label_print_required"] is True
    assert data["label_print_status"] == "LOCAL_AGENT_NOT_CONNECTED"
    assert data["return_label_no"].startswith("RTN-")
    assert data["return_management_no"] == data["return_label_no"]
    _assert_no_sensitive_values(response.json())


def test_upload_return_processing_attachment_and_list(
    client: TestClient,
    db_session: Session,
    upload_root: Path,
):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_attachment_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_attachment_admin",
        client_id=client_row.id,
    )

    response = client.post(
        f"/api/returns/processing/tasks/{task_id}/attachments",
        data={"attachment_type": "PHOTO", "note": "front photo"},
        files={"file": ("evidence.jpg", b"\xff\xd8\xff\xe0test-image", "image/jpeg")},
        headers=headers,
    )
    list_response = client.get(f"/api/returns/processing/tasks/{task_id}/attachments", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["task_id"] == task_id
    assert data["original_filename"] == "evidence.jpg"
    assert data["content_type"] == "image/jpeg"
    assert data["file_size"] > 0
    assert data["active_yn"] is True
    assert "storage_path" not in data
    assert list_response.status_code == 200
    items = list_response.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["attachment_id"] == data["attachment_id"]
    assert list(upload_root.rglob("*.jpg"))
    _assert_no_sensitive_values(response.json())


def test_disable_return_processing_attachment_hides_from_default_list(
    client: TestClient,
    db_session: Session,
    upload_root: Path,
):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_attachment_disable_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_attachment_disable_admin",
        client_id=client_row.id,
    )
    upload_response = client.post(
        f"/api/returns/processing/tasks/{task_id}/attachments",
        files={"file": ("evidence.png", b"\x89PNG\r\n\x1a\nimage", "image/png")},
        headers=headers,
    )
    attachment_id = upload_response.json()["data"]["attachment_id"]

    disable_response = client.post(
        f"/api/returns/processing/tasks/{task_id}/attachments/{attachment_id}/disable",
        headers=headers,
    )
    default_list_response = client.get(f"/api/returns/processing/tasks/{task_id}/attachments", headers=headers)
    inactive_list_response = client.get(
        f"/api/returns/processing/tasks/{task_id}/attachments?include_inactive=true",
        headers=headers,
    )

    assert disable_response.status_code == 200
    assert disable_response.json()["data"]["active_yn"] is False
    assert default_list_response.json()["data"]["items"] == []
    assert inactive_list_response.json()["data"]["items"][0]["active_yn"] is False


@pytest.mark.parametrize(
    ("filename", "content_type", "expected_code"),
    [
        ("evidence.exe", "image/jpeg", "RETURN_PROCESSING_ATTACHMENT_EXTENSION_INVALID"),
        ("evidence.jpg", "application/octet-stream", "RETURN_PROCESSING_ATTACHMENT_CONTENT_TYPE_INVALID"),
    ],
)
def test_upload_return_processing_attachment_blocks_unsafe_files(
    client: TestClient,
    db_session: Session,
    upload_root: Path,
    filename: str,
    content_type: str,
    expected_code: str,
):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id=f"return_attachment_block_{expected_code}",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id=f"return_attachment_block_{expected_code}",
        client_id=client_row.id,
    )

    response = client.post(
        f"/api/returns/processing/tasks/{task_id}/attachments",
        files={"file": (filename, b"unsafe-file", content_type)},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == expected_code
    assert not list(upload_root.rglob("*.*"))


def test_upload_return_processing_attachment_blocks_missing_task(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_user(
        db_session,
        login_id="return_attachment_missing_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers = _login(client, "return_attachment_missing_admin")

    response = client.post(
        "/api/returns/processing/tasks/999/attachments",
        files={"file": ("evidence.jpg", b"\xff\xd8\xff\xe0test-image", "image/jpeg")},
        headers=headers,
    )

    assert client_row.id
    assert response.status_code == 404
    assert response.json()["result_code"] == "RETURN_PROCESSING_ATTACHMENT_TASK_NOT_FOUND"


def test_upload_return_processing_attachment_blocks_invalid_validation_row(
    client: TestClient,
    db_session: Session,
    upload_root: Path,
):
    client_row = _create_client(db_session)
    _create_user(
        db_session,
        login_id="return_attachment_invalid_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers = _login(client, "return_attachment_invalid_admin")
    batch_id = _create_batch(client, db_session, "return_attachment_invalid_admin", client_row.id)
    client.post(
        f"/api/returns/intake/batches/{batch_id}/rows/paste",
        json={"rows": [{"row_no": 1, "order_no": "ORDER-BAD", "product_code": "P001", "qty": 0}]},
        headers=headers,
    )
    client.post(f"/api/returns/intake/batches/{batch_id}/validate", headers=headers)
    rows_response = client.get(f"/api/returns/intake/batches/{batch_id}/rows", headers=headers)
    row_id = rows_response.json()["data"]["items"][0]["row_id"]

    response = client.post(
        f"/api/returns/processing/tasks/{row_id}/attachments",
        files={"file": ("evidence.jpg", b"\xff\xd8\xff\xe0test-image", "image/jpeg")},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "RETURN_PROCESSING_ATTACHMENT_TASK_INVALID_VALIDATION"
    assert not list(upload_root.rglob("*.*"))


def test_judge_blocks_invalid_validation_row(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_user(
        db_session,
        login_id="return_judge_invalid_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers = _login(client, "return_judge_invalid_admin")
    batch_id = _create_batch(client, db_session, "return_judge_invalid_admin", client_row.id)
    client.post(
        f"/api/returns/intake/batches/{batch_id}/rows/paste",
        json={"rows": [{"row_no": 1, "order_no": "ORDER-BAD", "product_code": "P001", "qty": 0}]},
        headers=headers,
    )
    client.post(f"/api/returns/intake/batches/{batch_id}/validate", headers=headers)
    rows_response = client.get(f"/api/returns/intake/batches/{batch_id}/rows", headers=headers)
    row_id = rows_response.json()["data"]["items"][0]["row_id"]

    response = client.post(
        f"/api/returns/processing/tasks/{row_id}/judge",
        json={"judgement_status": "GOOD"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "RETURN_PROCESSING_TASK_INVALID_VALIDATION"


def test_judge_blocks_completed_task_and_invalid_judgement(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_judge_block_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers = _login(client, "return_judge_block_admin")
    batch_id = _create_batch(client, db_session, "return_judge_block_admin", client_row.id)
    client.post(f"/api/returns/intake/batches/{batch_id}/rows/paste", json=_rows_payload(), headers=headers)
    client.post(f"/api/returns/intake/batches/{batch_id}/validate", headers=headers)
    client.post(f"/api/returns/intake/batches/{batch_id}/prepare-processing", headers=headers)
    tasks_response = client.get(f"/api/returns/processing/tasks?batch_id={batch_id}", headers=headers)
    tasks = tasks_response.json()["data"]["items"]
    first_task_id = tasks[0]["task_id"]
    second_task_id = tasks[1]["task_id"]

    invalid_judgement_response = client.post(
        f"/api/returns/processing/tasks/{second_task_id}/judge",
        json={"judgement_status": "UNKNOWN"},
        headers=headers,
    )
    assert invalid_judgement_response.status_code == 400
    assert invalid_judgement_response.json()["result_code"] == "RETURN_PROCESSING_JUDGEMENT_INVALID"

    client.post(
        f"/api/returns/processing/tasks/{first_task_id}/judge",
        json={"judgement_status": "GOOD"},
        headers=headers,
    )
    completed_response = client.post(
        f"/api/returns/processing/tasks/{first_task_id}/judge",
        json={"judgement_status": "REFURB"},
        headers=headers,
    )

    assert completed_response.status_code == 400
    assert completed_response.json()["result_code"] == "RETURN_PROCESSING_TASK_ALREADY_COMPLETED"


def test_return_closing_candidates_show_completed_unreflected_rows(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_closing_candidates_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_closing_candidates_admin",
        client_id=client_row.id,
    )
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="GOOD")

    response = client.get("/api/returns/closing/candidates", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_count"] == 1
    item = data["items"][0]
    assert item["row_id"] == task_id
    assert item["judgement_status"] == "GOOD"
    assert item["inventory_reflected_yn"] is False
    assert item["closing_action"] == "INVENTORY_REFLECT_TARGET"
    _assert_no_sensitive_values(response.json())


def test_return_closing_confirm_good_creates_event_and_current_inventory(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    product = _create_product(db_session, client_row.id)
    warehouse = _create_warehouse_setting(db_session, client_id=client_row.id)
    _create_user(
        db_session,
        login_id="return_closing_good_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_closing_good_admin",
        client_id=client_row.id,
        rows_payload={"rows": [{"row_no": 1, "order_no": "ORDER-GOOD", "return_tracking_no": "RTN-GOOD", "product_code": "P001", "barcode": "880001", "qty": 2}]},
    )
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="GOOD")

    response = client.post("/api/returns/closing/confirm", json={"row_ids": [task_id]}, headers=headers)
    retry_response = client.post("/api/returns/closing/confirm", json={"row_ids": [task_id]}, headers=headers)
    row = db_session.query(ReturnIntakeRow).filter(ReturnIntakeRow.id == task_id).one()
    event = db_session.query(InventoryEvent).filter(InventoryEvent.source_id == task_id).one()
    current = (
        db_session.query(CurrentInventory)
        .filter(
            CurrentInventory.client_id == client_row.id,
            CurrentInventory.warehouse_id == warehouse.id,
            CurrentInventory.product_id == product.id,
            CurrentInventory.stock_status == "GOOD",
        )
        .one()
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["reflected_rows"] == 1
    assert data["event_count"] == 1
    assert row.inventory_reflected_yn is True
    assert row.inventory_event_id == event.id
    assert event.event_type == "RETURN_GOOD_IN"
    assert event.qty_delta == 2
    assert current.qty_on_hand == 2
    assert retry_response.status_code == 200
    retry_data = retry_response.json()["data"]
    assert retry_data["reflected_rows"] == 0
    assert retry_data["skipped_rows"] == 1
    assert db_session.query(InventoryEvent).filter(InventoryEvent.source_id == task_id).count() == 1


def test_return_closing_confirm_followup_judgement_does_not_increase_inventory(
    client: TestClient,
    db_session: Session,
):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_warehouse_setting(db_session, client_id=client_row.id)
    _create_user(
        db_session,
        login_id="return_closing_followup_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_closing_followup_admin",
        client_id=client_row.id,
    )
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="REFURB")

    response = client.post("/api/returns/closing/confirm", json={"row_ids": [task_id]}, headers=headers)
    row = db_session.query(ReturnIntakeRow).filter(ReturnIntakeRow.id == task_id).one()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["followup_rows"] == 1
    assert data["reflected_rows"] == 0
    assert row.inventory_reflected_yn is False
    assert db_session.query(InventoryEvent).count() == 0
    assert db_session.query(CurrentInventory).count() == 0


@pytest.mark.parametrize("judgement_status", ["REFURB", "SAMPLE", "MANUFACTURER_RETURN"])
def test_return_external_outbound_candidates_include_tracked_non_good_judgements(
    client: TestClient,
    db_session: Session,
    judgement_status: str,
):
    client_row = _create_client(db_session, code=f"CLIENT_{judgement_status}")
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id=f"return_outbound_candidate_{judgement_status}",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id=f"return_outbound_candidate_{judgement_status}",
        client_id=client_row.id,
    )
    judged = _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status=judgement_status)

    response = client.get("/api/returns/external-outbound/candidates", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_count"] == 1
    item = data["items"][0]
    assert item["row_id"] == task_id
    assert item["judgement_status"] == judgement_status
    assert item["return_management_no"] == judged["return_management_no"]
    assert item["external_outbound_required"] is True
    assert item["external_outbound_status"] == "READY"
    _assert_no_sensitive_values(response.json())


@pytest.mark.parametrize("judgement_status", ["GOOD", "HOLD", "DISPOSAL"])
def test_return_external_outbound_candidates_exclude_good_hold_and_disposal(
    client: TestClient,
    db_session: Session,
    judgement_status: str,
):
    client_row = _create_client(db_session, code=f"CLIENT_EXCLUDE_{judgement_status}")
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id=f"return_outbound_exclude_{judgement_status}",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id=f"return_outbound_exclude_{judgement_status}",
        client_id=client_row.id,
    )
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status=judgement_status)

    response = client.get("/api/returns/external-outbound/candidates", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_count"] == 0


def test_return_external_outbound_confirm_marks_confirmed_without_inventory_change(
    client: TestClient,
    db_session: Session,
):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_outbound_confirm_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_outbound_confirm_admin",
        client_id=client_row.id,
    )
    judged = _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="MANUFACTURER_RETURN")

    response = client.post(
        "/api/returns/external-outbound/confirm",
        json={"row_ids": [task_id], "scanned_numbers": [judged["return_management_no"]]},
        headers=headers,
    )
    retry_response = client.post(
        "/api/returns/external-outbound/confirm",
        json={"row_ids": [task_id], "scanned_numbers": [judged["return_management_no"]]},
        headers=headers,
    )
    row = db_session.query(ReturnIntakeRow).filter(ReturnIntakeRow.id == task_id).one()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["confirmed_rows"] == 1
    assert data["failed_rows"] == 0
    assert row.external_outbound_required is True
    assert row.external_outbound_status == "CONFIRMED"
    assert row.external_outbound_at is not None
    assert row.external_outbound_confirmed_by is not None
    assert db_session.query(InventoryEvent).count() == 0
    assert db_session.query(CurrentInventory).count() == 0
    assert retry_response.status_code == 200
    retry_data = retry_response.json()["data"]
    assert retry_data["confirmed_rows"] == 0
    assert retry_data["skipped_rows"] == 1


def test_return_external_outbound_confirm_fails_for_untracked_or_wrong_judgement_rows(
    client: TestClient,
    db_session: Session,
):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_outbound_fail_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_outbound_fail_admin",
        client_id=client_row.id,
    )
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="REFURB")
    row = db_session.query(ReturnIntakeRow).filter(ReturnIntakeRow.id == task_id).one()
    row.return_management_no = None
    row.return_label_no = None
    db_session.commit()

    no_number_response = client.get("/api/returns/external-outbound/candidates", headers=headers)
    failed_confirm_response = client.post(
        "/api/returns/external-outbound/confirm",
        json={"row_ids": [task_id]},
        headers=headers,
    )

    headers_good, _batch_id_good, good_task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_outbound_fail_admin",
        client_id=client_row.id,
    )
    _judge_processing_task(client, task_id=good_task_id, headers=headers_good, judgement_status="GOOD")
    wrong_judgement_response = client.post(
        "/api/returns/external-outbound/confirm",
        json={"row_ids": [good_task_id]},
        headers=headers_good,
    )

    missing_response = client.post(
        "/api/returns/external-outbound/confirm",
        json={"row_ids": [999999]},
        headers=headers,
    )

    assert no_number_response.status_code == 200
    assert no_number_response.json()["data"]["total_count"] == 0
    assert failed_confirm_response.status_code == 200
    assert failed_confirm_response.json()["data"]["failed_rows"] == 1
    assert "반품관리번호" in failed_confirm_response.json()["data"]["row_results"][0]["message"]
    assert wrong_judgement_response.status_code == 200
    assert wrong_judgement_response.json()["data"]["failed_rows"] == 1
    assert "외부반출 대상 판정" in wrong_judgement_response.json()["data"]["row_results"][0]["message"]
    assert missing_response.status_code == 200
    assert missing_response.json()["data"]["failed_rows"] == 1


def test_return_hold_candidates_include_hold_completed_rows(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_hold_candidates_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_hold_candidates_admin",
        client_id=client_row.id,
    )
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="HOLD")

    response = client.get("/api/returns/hold/candidates", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_count"] == 1
    item = data["items"][0]
    assert item["row_id"] == task_id
    assert item["judgement_status"] == "HOLD"
    assert item["hold_status"] == "HOLD_PENDING"
    assert item["return_management_no"]
    _assert_no_sensitive_values(response.json())


@pytest.mark.parametrize("judgement_status", ["GOOD", "REFURB", "SAMPLE", "MANUFACTURER_RETURN", "DISPOSAL"])
def test_return_hold_candidates_exclude_non_hold_judgements(
    client: TestClient,
    db_session: Session,
    judgement_status: str,
):
    client_row = _create_client(db_session, code=f"HOLD_EXCLUDE_{judgement_status}")
    _create_product(db_session, client_row.id)
    login_id = f"return_hold_exclude_{judgement_status.lower()}"
    _create_user(
        db_session,
        login_id=login_id,
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id=login_id,
        client_id=client_row.id,
    )
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status=judgement_status)

    response = client.get("/api/returns/hold/candidates", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["total_count"] == 0


def test_return_hold_update_saves_status_reason_and_response_memo(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_hold_update_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_hold_update_admin",
        client_id=client_row.id,
    )
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="HOLD")

    response = client.patch(
        f"/api/returns/hold/tasks/{task_id}",
        json={
            "hold_status": "CUSTOMER_CHECKING",
            "hold_reason": "상품 상태 확인 필요",
            "hold_response_memo": "고객사에 확인 요청",
        },
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["hold_status"] == "CUSTOMER_CHECKING"
    assert data["hold_reason"] == "상품 상태 확인 필요"
    assert data["hold_response_memo"] == "고객사에 확인 요청"
    row = db_session.get(ReturnIntakeRow, task_id)
    assert row is not None
    assert row.hold_status == "CUSTOMER_CHECKING"
    assert row.hold_reason == "상품 상태 확인 필요"
    assert row.hold_response_memo == "고객사에 확인 요청"


def test_return_hold_update_ready_to_rejudge_and_resolved_excludes_candidate(
    client: TestClient,
    db_session: Session,
):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_hold_ready_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_hold_ready_admin",
        client_id=client_row.id,
    )
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="HOLD")

    ready_response = client.patch(
        f"/api/returns/hold/tasks/{task_id}",
        json={"hold_status": "READY_TO_REJUDGE", "hold_reason": "재판정 준비", "hold_response_memo": "회신 완료"},
        headers=headers,
    )
    resolved_response = client.patch(
        f"/api/returns/hold/tasks/{task_id}",
        json={"hold_status": "RESOLVED", "hold_reason": "재판정 없이 해결", "hold_response_memo": "처리 종료"},
        headers=headers,
    )
    candidates_response = client.get("/api/returns/hold/candidates", headers=headers)

    assert ready_response.status_code == 200
    assert ready_response.json()["data"]["hold_status"] == "READY_TO_REJUDGE"
    assert resolved_response.status_code == 200
    assert resolved_response.json()["data"]["hold_status"] == "RESOLVED"
    assert resolved_response.json()["data"]["hold_resolved_at"] is not None
    assert candidates_response.status_code == 200
    assert candidates_response.json()["data"]["total_count"] == 0


def test_return_hold_update_blocks_non_hold_and_missing_task(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_hold_block_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_hold_block_admin",
        client_id=client_row.id,
    )
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="GOOD")

    non_hold_response = client.patch(
        f"/api/returns/hold/tasks/{task_id}",
        json={"hold_status": "CUSTOMER_CHECKING"},
        headers=headers,
    )
    missing_response = client.patch(
        "/api/returns/hold/tasks/999999",
        json={"hold_status": "CUSTOMER_CHECKING"},
        headers=headers,
    )

    assert non_hold_response.status_code == 400
    assert non_hold_response.json()["result_code"] == "RETURN_HOLD_INVALID_JUDGEMENT"
    assert missing_response.status_code == 404
    assert missing_response.json()["result_code"] == "RETURN_HOLD_TASK_NOT_FOUND"


def test_return_closing_confirm_good_fails_without_warehouse_setting(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_closing_no_warehouse_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_closing_no_warehouse_admin",
        client_id=client_row.id,
    )
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="GOOD")

    response = client.post("/api/returns/closing/confirm", json={"row_ids": [task_id]}, headers=headers)
    row = db_session.query(ReturnIntakeRow).filter(ReturnIntakeRow.id == task_id).one()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["failed_rows"] == 1
    assert "창고" in data["row_results"][0]["message"]
    assert row.inventory_reflected_yn is False
    assert db_session.query(InventoryEvent).count() == 0


def test_return_closing_confirm_good_fails_without_product(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_warehouse_setting(db_session, client_id=client_row.id)
    _create_user(
        db_session,
        login_id="return_closing_no_product_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_closing_no_product_admin",
        client_id=client_row.id,
        rows_payload={"rows": [{"row_no": 1, "order_no": "ORDER-NO-PRODUCT", "return_tracking_no": "RTN-NO-PRODUCT", "product_code": "UNKNOWN", "qty": 1}]},
    )
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="GOOD")

    response = client.post("/api/returns/closing/confirm", json={"row_ids": [task_id]}, headers=headers)
    row = db_session.query(ReturnIntakeRow).filter(ReturnIntakeRow.id == task_id).one()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["failed_rows"] == 1
    assert "상품" in data["row_results"][0]["message"]
    assert row.inventory_reflected_yn is False
    assert db_session.query(InventoryEvent).count() == 0


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
