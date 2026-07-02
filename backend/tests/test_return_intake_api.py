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
from app.models.master import (
    Agency,
    Client,
    ClientUnit,
    ClientWarehouseSetting,
    Product,
    ProductBarcode,
    ReturnJudgmentWarehouseRoute,
    Warehouse,
)
from app.models.returns import (
    ReturnExternalOutboundBatch,
    ReturnIntakeBatch,
    ReturnIntakeRow,
    ReturnProcessingAttachment,
)
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
        Agency.__table__,
        Client.__table__,
        Warehouse.__table__,
        ClientUnit.__table__,
        ReturnJudgmentWarehouseRoute.__table__,
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
        ReturnExternalOutboundBatch.__table__,
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
    agency = Agency(agency_code=f"AGENCY_{code}", agency_name=f"{code} Agency", active_yn=True)
    row = Client(client_code=code, client_name=f"{code} Name", agency_id=None, active_yn=active_yn)
    db.add_all([agency, row])
    db.flush()
    row.agency_id = agency.id
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
    return [
        "RETURN_VIEW",
        "RETURN_PREPARE",
        "RETURN_PROCESS",
        "RETURN_JUDGE",
        "RETURN_CLOSE",
        "RETURN_OUTBOUND",
    ]


def _client_return_permissions() -> list[str]:
    return ["RETURN_VIEW", "RETURN_CLIENT_SUBMIT", "RETURN_TRACE"]


def _create_product(db: Session, client_id: int, code: str = "P001", barcode: str = "880001") -> Product:
    product = Product(
        agency_id=db.get(Client, client_id).agency_id if db.get(Client, client_id) is not None else None,
        client_id=client_id,
        product_code=code,
        product_name="Test Product",
        barcode=barcode,
        active_yn=True,
    )
    db.add(product)
    db.flush()
    product_barcode = ProductBarcode(
        agency_id=product.agency_id,
        client_id=client_id,
        product_id=product.id,
        barcode="880002",
        barcode_norm="880002",
        barcode_type="EA",
        unit_qty=1,
        active_yn=True,
    )
    db.add(product_barcode)
    for judgement_code in ("GOOD", "REFURB", "REFURB_A", "REFURB_B", "REFURB_C", "SAMPLE", "MANUFACTURER_RETURN", "DISPOSAL", "HOLD"):
        warehouse = Warehouse(
            warehouse_code=f"WH-{client_id}-{judgement_code}",
            warehouse_name=f"{judgement_code} Warehouse",
            warehouse_type="RETURN",
            active_yn=True,
        )
        db.add(warehouse)
        db.flush()
        db.add(
            ClientWarehouseSetting(
                agency_id=product.agency_id,
                client_id=client_id,
                warehouse_id=warehouse.id,
                usage_type=f"RETURN_ROUTE_{judgement_code}",
                is_default=False,
                active_yn=True,
            )
        )
        db.add(
            ReturnJudgmentWarehouseRoute(
                agency_id=product.agency_id,
                client_id=client_id,
                client_unit_id=None,
                judgment_code=judgement_code,
                warehouse_id=warehouse.id,
                active_yn=True,
                sort_order=100,
            )
        )
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
            agency_id=db.get(Client, client_id).agency_id if db.get(Client, client_id) is not None else None,
            client_id=client_id,
            warehouse_id=warehouse.id,
            usage_type=usage_type,
            is_default=True,
            active_yn=True,
        )
    )
    db.commit()
    return warehouse


def _create_return_warehouse_route(
    db: Session,
    *,
    client_id: int,
    warehouse_id: int,
    judgement_code: str = "GOOD",
    client_unit_id: int | None = None,
) -> ReturnJudgmentWarehouseRoute:
    route = ReturnJudgmentWarehouseRoute(
        agency_id=db.get(Client, client_id).agency_id if db.get(Client, client_id) is not None else None,
        client_id=client_id,
        client_unit_id=client_unit_id,
        judgment_code=judgement_code,
        warehouse_id=warehouse_id,
        active_yn=True,
        sort_order=1,
    )
    db.add(route)
    db.commit()
    return route


def _create_client_unit(db: Session, client_id: int, code: str = "ONLINE", active_yn: bool = True) -> ClientUnit:
    unit = ClientUnit(
        agency_id=db.get(Client, client_id).agency_id if db.get(Client, client_id) is not None else None,
        client_id=client_id,
        unit_code=code,
        unit_name=f"{code} Team",
        unit_type="TEAM",
        active_yn=active_yn,
    )
    db.add(unit)
    db.commit()
    return unit


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
    assign_client_unit: bool = True,
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
    if assign_client_unit:
        row = db.get(ReturnIntakeRow, task_id)
        if row is not None and row.client_unit_id is None:
            unit = _create_client_unit(db, client_id, code=f"AUTO_{task_id}")
            row.client_unit_id = unit.id
            db.commit()
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


def _mark_row_inventory_reflected_for_test(
    db: Session,
    *,
    task_id: int,
    stock_status: str,
) -> InventoryEvent:
    row = db.get(ReturnIntakeRow, task_id)
    assert row is not None
    product = None
    if row.product_code:
        product = (
            db.query(Product)
            .filter(Product.client_id == row.client_id, Product.product_code == row.product_code)
            .one_or_none()
        )
    if product is None and row.barcode:
        product_barcode = (
            db.query(ProductBarcode)
            .filter(ProductBarcode.client_id == row.client_id, ProductBarcode.barcode == row.barcode)
            .one_or_none()
        )
        if product_barcode is not None:
            product = db.get(Product, product_barcode.product_id)
    if product is None:
        product = db.query(Product).filter(Product.client_id == row.client_id).order_by(Product.id).first()
    assert product is not None
    if row.client_unit_id is None:
        unit = _create_client_unit(db, row.client_id, code=f"AUTO_{task_id}")
        row.client_unit_id = unit.id
    if row.final_warehouse_id is None:
        warehouse = _create_warehouse_setting(
            db,
            client_id=row.client_id,
            usage_type=f"RETURN_{stock_status}_{task_id}",
        )
        row.final_warehouse_id = warehouse.id
    else:
        warehouse = db.get(Warehouse, row.final_warehouse_id)
        assert warehouse is not None
    qty = row.qty or 1
    event = InventoryEvent(
        event_no=f"RTN-CLOSE-TEST-{task_id}-{stock_status}",
        agency_id=row.agency_id,
        client_id=row.client_id,
        warehouse_id=warehouse.id,
        location_id=None,
        product_id=product.id,
        product_code=product.product_code,
        stock_status=stock_status,
        event_type="RETURN_JUDGEMENT_IN",
        qty_delta=qty,
        source_type="RETURN_CLOSING",
        source_id=row.id,
        source_line_id=row.id,
        idempotency_key=f"return-closing-test:{row.id}:{stock_status.lower()}",
        event_reason="test setup",
        created_by=1,
        raw_json={},
    )
    db.add(event)
    db.flush()
    row.inventory_reflected_yn = True
    row.inventory_event_id = event.id
    db.add(
        CurrentInventory(
            agency_id=row.agency_id,
            client_id=row.client_id,
            warehouse_id=warehouse.id,
            location_id=None,
            product_id=product.id,
            stock_status=stock_status,
            qty_on_hand=qty,
        )
    )
    db.commit()
    return event


def _prepare_hold_ready_to_rejudge_task(
    client: TestClient,
    db: Session,
    *,
    login_id: str,
    client_id: int,
) -> tuple[dict[str, str], int, int]:
    headers, batch_id, task_id = _prepare_processing_task(
        client,
        db,
        login_id=login_id,
        client_id=client_id,
    )
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="HOLD")
    response = client.patch(
        f"/api/returns/hold/tasks/{task_id}",
        json={
            "hold_status": "READY_TO_REJUDGE",
            "hold_reason": "rejudge ready",
            "hold_response_memo": "customer checked",
        },
        headers=headers,
    )
    assert response.status_code == 200
    return headers, batch_id, task_id


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


def test_client_user_can_submit_own_return_intake_but_not_other_client(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, "CLIENT_PORTAL_A")
    other_client = _create_client(db_session, "CLIENT_PORTAL_B")
    _create_user(
        db_session,
        login_id="client_portal_submit_user",
        role_code="CLIENT_USER",
        permissions=_client_return_permissions(),
        client_id=client_row.id,
    )
    headers = _login(client, "client_portal_submit_user")

    create_response = client.post(
        "/api/returns/intake/batches",
        json={"client_id": client_row.id, "source_type": "PASTE", "source_name": "portal paste"},
        headers=headers,
    )
    assert create_response.status_code == 200
    batch_id = create_response.json()["data"]["batch_id"]
    assert create_response.json()["data"]["client_id"] == client_row.id

    paste_response = client.post(
        f"/api/returns/intake/batches/{batch_id}/rows/paste",
        json=_rows_payload(),
        headers=headers,
    )
    validate_response = client.post(f"/api/returns/intake/batches/{batch_id}/validate", headers=headers)
    cross_client_response = client.post(
        "/api/returns/intake/batches",
        json={"client_id": other_client.id, "source_type": "PASTE"},
        headers=headers,
    )

    assert paste_response.status_code == 200
    assert validate_response.status_code == 200
    assert cross_client_response.status_code == 403
    assert cross_client_response.json()["result_code"] == "CLIENT_SCOPE_DENIED"


def test_client_admin_without_portal_submit_permission_is_blocked(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, "CLIENT_PORTAL_NO_PERMISSION")
    _create_user(
        db_session,
        login_id="client_portal_no_permission_admin",
        role_code="CLIENT_ADMIN",
        permissions=["RETURN_VIEW", "RETURN_TRACE"],
        client_id=client_row.id,
    )

    response = client.post(
        "/api/returns/intake/batches",
        json={"client_id": client_row.id, "source_type": "PASTE"},
        headers=_login(client, "client_portal_no_permission_admin"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "PERMISSION_DENIED"


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


def test_paste_rows_saves_client_unit_assignment(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    unit = _create_client_unit(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_unit_paste_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers = _login(client, "return_unit_paste_admin")
    create_response = client.post(
        "/api/returns/intake/batches",
        json={"client_id": client_row.id, "client_unit_id": unit.id, "source_type": "PASTE"},
        headers=headers,
    )
    assert create_response.status_code == 200
    batch_id = create_response.json()["data"]["batch_id"]

    response = client.post(
        f"/api/returns/intake/batches/{batch_id}/rows/paste",
        json=_rows_payload(client_unit_id=unit.id),
        headers=headers,
    )
    rows_response = client.get(f"/api/returns/intake/batches/{batch_id}/rows", headers=headers)

    assert response.status_code == 200
    rows = rows_response.json()["data"]["items"]
    assert rows[0]["client_unit_id"] == unit.id
    assert rows[0]["team_assign_status"] == "ASSIGNED"


def test_unit_assignment_pending_row_can_be_assigned(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    unit = _create_client_unit(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_unit_assign_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers = _login(client, "return_unit_assign_admin")
    batch_id = _create_batch(client, db_session, "return_unit_assign_admin", client_row.id)
    paste_response = client.post(
        f"/api/returns/intake/batches/{batch_id}/rows/paste",
        json=_rows_payload(),
        headers=headers,
    )
    assert paste_response.status_code == 200

    pending_response = client.get("/api/returns/intake/unit-assignment-pending", headers=headers)
    assert pending_response.status_code == 200
    pending_rows = pending_response.json()["data"]["items"]
    assert len(pending_rows) == 2
    assert pending_rows[0]["team_assign_status"] == "TEAM_ASSIGN_PENDING"

    assign_response = client.post(
        f"/api/returns/intake/rows/{pending_rows[0]['row_id']}/assign-unit",
        json={"client_unit_id": unit.id},
        headers=headers,
    )
    assert assign_response.status_code == 200
    assert assign_response.json()["data"]["client_unit_id"] == unit.id
    assert assign_response.json()["data"]["team_assign_status"] == "ASSIGNED"

    next_pending = client.get("/api/returns/intake/unit-assignment-pending", headers=headers)
    assert next_pending.status_code == 200
    assert len(next_pending.json()["data"]["items"]) == 1


def test_unit_assignment_rejects_already_assigned_row(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    unit = _create_client_unit(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_unit_assigned_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers = _login(client, "return_unit_assigned_admin")
    create_response = client.post(
        "/api/returns/intake/batches",
        json={"client_id": client_row.id, "client_unit_id": unit.id, "source_type": "PASTE"},
        headers=headers,
    )
    assert create_response.status_code == 200
    batch_id = create_response.json()["data"]["batch_id"]
    client.post(
        f"/api/returns/intake/batches/{batch_id}/rows/paste",
        json=_rows_payload(client_unit_id=unit.id),
        headers=headers,
    )
    rows_response = client.get(f"/api/returns/intake/batches/{batch_id}/rows", headers=headers)
    row_id = rows_response.json()["data"]["items"][0]["row_id"]

    assign_response = client.post(
        f"/api/returns/intake/rows/{row_id}/assign-unit",
        json={"client_unit_id": unit.id},
        headers=headers,
    )

    assert assign_response.status_code == 400
    assert assign_response.json()["result_code"] == "RETURN_INTAKE_ROW_UNIT_ALREADY_ASSIGNED"


def test_unit_assignment_rejects_prepared_row(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    unit = _create_client_unit(db_session, client_row.id)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_unit_prepared_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers = _login(client, "return_unit_prepared_admin")
    batch_id = _create_batch(client, db_session, "return_unit_prepared_admin", client_row.id)
    client.post(f"/api/returns/intake/batches/{batch_id}/rows/paste", json=_rows_payload(), headers=headers)
    client.post(f"/api/returns/intake/batches/{batch_id}/validate", headers=headers)
    prepare_response = client.post(f"/api/returns/intake/batches/{batch_id}/prepare-processing", headers=headers)
    assert prepare_response.status_code == 200
    rows_response = client.get(f"/api/returns/intake/batches/{batch_id}/rows", headers=headers)
    row_id = rows_response.json()["data"]["items"][0]["row_id"]

    assign_response = client.post(
        f"/api/returns/intake/rows/{row_id}/assign-unit",
        json={"client_unit_id": unit.id},
        headers=headers,
    )

    assert assign_response.status_code == 400
    assert assign_response.json()["result_code"] == "RETURN_INTAKE_ROW_UNIT_ASSIGNMENT_NOT_ALLOWED"


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


def test_client_user_cannot_confirm_internal_return_processing(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, "CLIENT_BLOCK_PROCESSING")
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="processing_owner_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    _create_user(
        db_session,
        login_id="processing_blocked_client_user",
        role_code="CLIENT_USER",
        permissions=_client_return_permissions(),
        client_id=client_row.id,
    )
    _headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="processing_owner_admin",
        client_id=client_row.id,
    )

    response = client.post(
        f"/api/returns/processing/tasks/{task_id}/judge",
        json={"judgement_status": "GOOD"},
        headers=_login(client, "processing_blocked_client_user"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "PERMISSION_DENIED"


def test_client_admin_cannot_confirm_return_closing(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, "CLIENT_BLOCK_CLOSING")
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="closing_owner_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    _create_user(
        db_session,
        login_id="closing_blocked_client_admin",
        role_code="CLIENT_ADMIN",
        permissions=_client_return_permissions(),
        client_id=client_row.id,
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="closing_owner_admin",
        client_id=client_row.id,
    )
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="GOOD")

    response = client.post(
        "/api/returns/closing/confirm",
        json={"row_ids": [task_id]},
        headers=_login(client, "closing_blocked_client_admin"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "PERMISSION_DENIED"


def test_client_user_cannot_confirm_external_outbound(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, "CLIENT_BLOCK_OUTBOUND")
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="outbound_owner_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    _create_user(
        db_session,
        login_id="outbound_blocked_client_user",
        role_code="CLIENT_USER",
        permissions=_client_return_permissions(),
        client_id=client_row.id,
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="outbound_owner_admin",
        client_id=client_row.id,
    )
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="MANUFACTURER_RETURN")

    response = client.post(
        "/api/returns/external-outbound/confirm",
        json={"row_ids": [task_id]},
        headers=_login(client, "outbound_blocked_client_user"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "PERMISSION_DENIED"


def test_client_user_cannot_confirm_return_disposal(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, "CLIENT_BLOCK_DISPOSAL")
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="disposal_owner_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    _create_user(
        db_session,
        login_id="disposal_blocked_client_user",
        role_code="CLIENT_USER",
        permissions=_client_return_permissions(),
        client_id=client_row.id,
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="disposal_owner_admin",
        client_id=client_row.id,
    )
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="DISPOSAL")

    response = client.post(
        f"/api/returns/disposal/tasks/{task_id}/confirm",
        json={"disposal_reason": "blocked"},
        headers=_login(client, "disposal_blocked_client_user"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "PERMISSION_DENIED"


def test_internal_worker_can_confirm_processing_with_operation_permission(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, "WORKER_PROCESSING")
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="worker_prepare_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    _create_user(
        db_session,
        login_id="worker_processing_user",
        role_code="INTERNAL_WORKER",
        permissions=["RETURN_VIEW", "RETURN_PROCESS", "RETURN_JUDGE"],
    )
    _headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="worker_prepare_admin",
        client_id=client_row.id,
    )

    response = client.post(
        f"/api/returns/processing/tasks/{task_id}/judge",
        json={"judgement_status": "GOOD"},
        headers=_login(client, "worker_processing_user"),
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "COMPLETED"


def test_manual_processing_row_creates_and_increments_no_detail_return(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, "NO_DETAIL_CLIENT")
    product = _create_product(db_session, client_id=client_row.id, code="ND-P001", barcode="ND-BC001")
    _create_warehouse_setting(db_session, client_id=client_row.id)
    _create_user(db_session, login_id="manual_no_detail_admin", role_code="INTERNAL_ADMIN", permissions=_return_permissions())
    headers = _login(client, "manual_no_detail_admin")

    first_response = client.post(
        "/api/returns/processing/manual-rows",
        json={
            "client_id": client_row.id,
            "return_tracking_no": "ND-TRACK-001",
            "barcode": product.barcode,
            "quantity": 1,
            "processing_method": "SCAN",
        },
        headers=headers,
    )
    assert first_response.status_code == 200
    first_data = first_response.json()["data"]
    assert first_data["created"] is True
    assert first_data["qty"] == 1
    assert first_data["processing_mode"] == "NO_DETAIL_MANUAL_INTAKE"
    assert first_data["processing_method"] == "SCAN"

    second_response = client.post(
        "/api/returns/processing/manual-rows",
        json={
            "client_id": client_row.id,
            "return_tracking_no": "ND-TRACK-001",
            "barcode": product.barcode,
            "quantity": 1,
            "processing_method": "SCAN",
        },
        headers=headers,
    )
    assert second_response.status_code == 200
    second_data = second_response.json()["data"]
    assert second_data["created"] is False
    assert second_data["task_id"] == first_data["task_id"]
    assert second_data["qty"] == 2

    current_count = db_session.query(CurrentInventory).count()
    judge_response = client.post(
        f"/api/returns/processing/tasks/{first_data['task_id']}/judge",
        json={"judgement_status": "GOOD", "processing_method": "SCAN"},
        headers=headers,
    )
    assert judge_response.status_code == 200
    judged = judge_response.json()["data"]
    assert judged["status"] == "COMPLETED"
    assert judged["final_warehouse_id"] is not None
    assert judged["processing_method"] == "SCAN"
    assert db_session.query(CurrentInventory).count() == current_count


def test_manual_processing_row_blocks_unknown_product(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, "NO_DETAIL_UNKNOWN")
    _create_user(db_session, login_id="manual_unknown_admin", role_code="INTERNAL_ADMIN", permissions=_return_permissions())
    headers = _login(client, "manual_unknown_admin")

    response = client.post(
        "/api/returns/processing/manual-rows",
        json={
            "client_id": client_row.id,
            "return_tracking_no": "ND-UNKNOWN-001",
            "barcode": "NO-SUCH-BARCODE",
            "quantity": 1,
            "processing_method": "SCAN",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "RETURN_PROCESSING_MANUAL_PRODUCT_NOT_FOUND"


def test_processing_judge_blocks_without_confirmed_warehouse(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, "NO_WAREHOUSE_CLIENT")
    product = Product(
        client_id=client_row.id,
        product_code="NW-P001",
        product_name="No Warehouse Product",
        barcode="NW-BC001",
        active_yn=True,
    )
    db_session.add(product)
    db_session.commit()
    _create_user(db_session, login_id="no_warehouse_admin", role_code="INTERNAL_ADMIN", permissions=_return_permissions())
    headers = _login(client, "no_warehouse_admin")

    manual_response = client.post(
        "/api/returns/processing/manual-rows",
        json={
            "client_id": client_row.id,
            "return_tracking_no": "NW-TRACK-001",
            "barcode": "NW-BC001",
            "quantity": 1,
            "processing_method": "SCAN",
        },
        headers=headers,
    )
    assert manual_response.status_code == 200
    task_id = manual_response.json()["data"]["task_id"]

    judge_response = client.post(
        f"/api/returns/processing/tasks/{task_id}/judge",
        json={"judgement_status": "GOOD", "processing_method": "SCAN"},
        headers=headers,
    )

    assert judge_response.status_code == 400
    assert judge_response.json()["result_code"] == "RETURN_PROCESSING_WAREHOUSE_REQUIRED"


def test_judge_good_completes_task_without_label(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_warehouse_setting(db_session, client_id=client_row.id)
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
    assert data["agency_id"] == client_row.agency_id
    assert data["original_filename"] == "evidence.jpg"
    assert data["content_type"] == "image/jpeg"
    assert data["file_size"] > 0
    assert data["active_yn"] is True
    assert "storage_path" not in data
    assert list_response.status_code == 200
    items = list_response.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["attachment_id"] == data["attachment_id"]
    assert items[0]["agency_id"] == client_row.agency_id
    attachment = db_session.query(ReturnProcessingAttachment).filter(ReturnProcessingAttachment.id == data["attachment_id"]).one()
    assert attachment.agency_id == client_row.agency_id
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
            CurrentInventory.warehouse_id == event.warehouse_id,
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


def test_return_closing_uses_team_route_before_client_route(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, code="CLIENT_ROUTE_CLOSE")
    product = _create_product(db_session, client_row.id)
    default_warehouse = _create_warehouse_setting(db_session, client_id=client_row.id, usage_type="RETURN_GOOD")
    team_warehouse = _create_warehouse_setting(db_session, client_id=client_row.id, usage_type="RETURN_GOOD_TEAM")
    unit = _create_client_unit(db_session, client_row.id, code="ONLINE")
    _create_return_warehouse_route(db_session, client_id=client_row.id, warehouse_id=default_warehouse.id, judgement_code="GOOD")
    team_route = _create_return_warehouse_route(
        db_session,
        client_id=client_row.id,
        client_unit_id=unit.id,
        warehouse_id=team_warehouse.id,
        judgement_code="GOOD",
    )
    _create_user(
        db_session,
        login_id="return_closing_team_route_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_closing_team_route_admin",
        client_id=client_row.id,
        rows_payload={
            "client_unit_id": unit.id,
            "rows": [
                {
                    "row_no": 1,
                    "order_no": "ORDER-TEAM-ROUTE",
                    "return_tracking_no": "RTN-TEAM-ROUTE",
                    "product_code": product.product_code,
                    "barcode": product.barcode,
                    "qty": 1,
                }
            ],
        },
    )

    judge_response = _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="GOOD")
    response = client.post("/api/returns/closing/confirm", json={"row_ids": [task_id]}, headers=headers)
    row = db_session.query(ReturnIntakeRow).filter(ReturnIntakeRow.id == task_id).one()
    event = db_session.query(InventoryEvent).filter(InventoryEvent.source_id == task_id).one()
    current = (
        db_session.query(CurrentInventory)
        .filter(
            CurrentInventory.client_id == client_row.id,
            CurrentInventory.warehouse_id == team_warehouse.id,
            CurrentInventory.product_id == product.id,
            CurrentInventory.stock_status == "GOOD",
        )
        .one()
    )

    assert judge_response["recommended_warehouse_id"] == team_warehouse.id
    assert judge_response["warehouse_route_id"] == team_route.id
    assert response.status_code == 200
    assert response.json()["data"]["reflected_rows"] == 1
    assert response.json()["data"]["row_results"][0]["warehouse_id"] == team_warehouse.id
    assert row.warehouse_route_id == team_route.id
    assert event.warehouse_id == team_warehouse.id
    assert current.qty_on_hand == 1


def test_return_processing_judge_fails_without_route_when_no_default_warehouse(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, code="CLIENT_NO_ROUTE")
    product = Product(
        client_id=client_row.id,
        product_code="NO-ROUTE-P001",
        product_name="No Route Product",
        barcode="NO-ROUTE-BC001",
        active_yn=True,
    )
    db_session.add(product)
    db_session.commit()
    _create_user(
        db_session,
        login_id="return_closing_no_route_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_closing_no_route_admin",
        client_id=client_row.id,
        rows_payload={
            "rows": [
                {
                    "row_no": 1,
                    "order_no": "ORDER-NO-ROUTE",
                    "return_tracking_no": "RTN-NO-ROUTE",
                    "product_code": product.product_code,
                    "barcode": product.barcode,
                    "qty": 1,
                }
            ]
        },
    )
    response = client.post(
        f"/api/returns/processing/tasks/{task_id}/judge",
        json={"judgement_status": "GOOD"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "RETURN_PROCESSING_WAREHOUSE_REQUIRED"
    assert db_session.query(InventoryEvent).filter(InventoryEvent.source_id == task_id).count() == 0


def test_current_inventory_requires_auth(client: TestClient):
    response = client.get("/api/inventory/current")

    assert response.status_code == 401
    assert response.json()["result_code"] == "NOT_AUTHENTICATED"


def test_current_inventory_lists_good_closing_result_with_filters(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    product = _create_product(db_session, client_row.id)
    warehouse = _create_warehouse_setting(db_session, client_id=client_row.id)
    _create_user(
        db_session,
        login_id="inventory_current_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions() + ["INVENTORY_VIEW"],
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="inventory_current_admin",
        client_id=client_row.id,
        rows_payload={
            "rows": [
                {
                    "row_no": 1,
                    "order_no": "ORDER-INVENTORY",
                    "return_tracking_no": "RTN-INVENTORY",
                    "product_code": product.product_code,
                    "barcode": product.barcode,
                    "qty": 3,
                }
            ]
        },
    )
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="GOOD")
    close_response = client.post("/api/returns/closing/confirm", json={"row_ids": [task_id]}, headers=headers)
    event = db_session.query(InventoryEvent).filter(InventoryEvent.source_id == task_id).one()
    actual_warehouse = db_session.get(Warehouse, event.warehouse_id)
    assert actual_warehouse is not None

    response = client.get(
        (
            "/api/inventory/current"
            f"?client_id={client_row.id}"
            f"&warehouse_id={event.warehouse_id}"
            "&stock_status=GOOD"
            "&keyword=P001"
        ),
        headers=headers,
    )
    product_code_response = client.get("/api/inventory/current?product_code=P001", headers=headers)
    barcode_response = client.get("/api/inventory/current?barcode=880001", headers=headers)

    assert close_response.status_code == 200
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_count"] == 1
    item = data["items"][0]
    assert item["inventory_id"] is not None
    assert item["client_id"] == client_row.id
    assert item["client_name"] == client_row.client_name
    assert item["warehouse_id"] == event.warehouse_id
    assert item["warehouse_code"] == actual_warehouse.warehouse_code
    assert item["product_id"] == product.id
    assert item["product_code"] == product.product_code
    assert item["product_name"] == product.product_name
    assert item["barcode"] == product.barcode
    assert item["stock_status"] == "GOOD"
    assert item["qty"] == 3
    assert product_code_response.json()["data"]["total_count"] == 1
    assert barcode_response.json()["data"]["total_count"] == 1
    _assert_no_sensitive_values(response.json())


def test_inventory_events_requires_auth(client: TestClient):
    response = client.get("/api/inventory/events")

    assert response.status_code == 401
    assert response.json()["result_code"] == "NOT_AUTHENTICATED"


def test_inventory_events_lists_good_closing_event_with_filters(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    product = _create_product(db_session, client_row.id)
    warehouse = _create_warehouse_setting(db_session, client_id=client_row.id)
    _create_user(
        db_session,
        login_id="inventory_events_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions() + ["INVENTORY_VIEW"],
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="inventory_events_admin",
        client_id=client_row.id,
        rows_payload={
            "rows": [
                {
                    "row_no": 1,
                    "order_no": "ORDER-EVENT",
                    "return_tracking_no": "RTN-EVENT",
                    "product_code": product.product_code,
                    "barcode": product.barcode,
                    "qty": 4,
                }
            ]
        },
    )
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="GOOD")
    close_response = client.post("/api/returns/closing/confirm", json={"row_ids": [task_id]}, headers=headers)
    event = db_session.query(InventoryEvent).filter(InventoryEvent.source_id == task_id).one()
    actual_warehouse = db_session.get(Warehouse, event.warehouse_id)
    assert actual_warehouse is not None

    response = client.get(
        (
            "/api/inventory/events"
            f"?client_id={client_row.id}"
            f"&warehouse_id={event.warehouse_id}"
            "&event_type=RETURN_GOOD_IN"
            "&source_type=RETURN_CLOSING"
            "&keyword=P001"
        ),
        headers=headers,
    )
    product_code_response = client.get("/api/inventory/events?product_code=P001", headers=headers)
    barcode_response = client.get("/api/inventory/events?barcode=880001", headers=headers)
    source_response = client.get(f"/api/inventory/events?keyword=return-closing:{task_id}:good", headers=headers)

    assert close_response.status_code == 200
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_count"] == 1
    item = data["items"][0]
    assert item["event_id"] is not None
    assert item["event_no"] == f"RTN-CLOSE-{task_id}"
    assert item["client_id"] == client_row.id
    assert item["client_name"] == client_row.client_name
    assert item["warehouse_id"] == event.warehouse_id
    assert item["warehouse_code"] == actual_warehouse.warehouse_code
    assert item["product_id"] == product.id
    assert item["product_code"] == product.product_code
    assert item["product_name"] == product.product_name
    assert item["barcode"] == product.barcode
    assert item["event_type"] == "RETURN_GOOD_IN"
    assert item["source_type"] == "RETURN_CLOSING"
    assert item["source_id"] == task_id
    assert item["source_line_id"] == task_id
    assert item["stock_status"] == "GOOD"
    assert item["qty"] == 4
    assert item["idempotency_key"] == f"return-closing:{task_id}:good"
    assert item["created_by"] is not None
    assert product_code_response.json()["data"]["total_count"] == 1
    assert barcode_response.json()["data"]["total_count"] == 1
    assert source_response.json()["data"]["total_count"] == 1
    _assert_no_sensitive_values(response.json())


def test_return_history_requires_auth(client: TestClient):
    response = client.get("/api/returns/history")

    assert response.status_code == 401
    assert response.json()["result_code"] == "NOT_AUTHENTICATED"


def test_return_history_lists_good_reflected_row_without_customer_private_fields(
    client: TestClient,
    db_session: Session,
):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_warehouse_setting(db_session, client_id=client_row.id)
    _create_user(
        db_session,
        login_id="return_history_good_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_history_good_admin",
        client_id=client_row.id,
        rows_payload={
            "rows": [
                {
                    "row_no": 1,
                    "order_no": "ORDER-HISTORY-GOOD",
                    "return_tracking_no": "RTN-HISTORY-GOOD",
                    "product_code": "P001",
                    "barcode": "880001",
                    "qty": 1,
                    "customer_name": "민감고객",
                    "customer_phone": "010-1111-2222",
                }
            ]
        },
    )
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="GOOD")
    close_response = client.post("/api/returns/closing/confirm", json={"row_ids": [task_id]}, headers=headers)

    response = client.get(
        (
            "/api/returns/history"
            f"?client_id={client_row.id}"
            "&keyword=RTN-HISTORY-GOOD"
            "&judgement_status=GOOD"
            "&followup_status=INVENTORY_REFLECTED"
        ),
        headers=headers,
    )

    assert close_response.status_code == 200
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_count"] == 1
    item = data["items"][0]
    assert item["row_id"] == task_id
    assert item["client_name"] == client_row.client_name
    assert item["judgement_status"] == "GOOD"
    assert item["inventory_reflected_yn"] is True
    assert item["followup_status"] == "INVENTORY_REFLECTED"
    assert item["followup_status_label"] == "정상재고반영"
    assert "customer_name" not in item
    assert "customer_phone_masked" not in item
    assert "raw_data" not in item
    _assert_no_sensitive_values(response.json())


def test_return_history_summarizes_outbound_hold_and_disposal_followup_statuses(
    client: TestClient,
    db_session: Session,
):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_history_followup_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )

    outbound_headers, _outbound_batch_id, outbound_task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_history_followup_admin",
        client_id=client_row.id,
        rows_payload={
            "rows": [
                {
                    "row_no": 1,
                    "order_no": "ORDER-HISTORY-OUT",
                    "return_tracking_no": "RTN-HISTORY-OUT",
                    "product_code": "P001",
                    "barcode": "880001",
                    "qty": 1,
                }
            ]
        },
    )
    outbound_judged = _judge_processing_task(
        client,
        task_id=outbound_task_id,
        headers=outbound_headers,
        judgement_status="MANUFACTURER_RETURN",
    )
    _mark_row_inventory_reflected_for_test(
        db_session,
        task_id=outbound_task_id,
        stock_status="MANUFACTURER_RETURN",
    )
    outbound_confirm = client.post(
        "/api/returns/external-outbound/confirm",
        json={"row_ids": [outbound_task_id], "scanned_numbers": [outbound_judged["return_management_no"]]},
        headers=outbound_headers,
    )

    hold_headers, _hold_batch_id, hold_task_id = _prepare_hold_ready_to_rejudge_task(
        client,
        db_session,
        login_id="return_history_followup_admin",
        client_id=client_row.id,
    )

    disposal_headers, _disposal_batch_id, disposal_task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_history_followup_admin",
        client_id=client_row.id,
        rows_payload={
            "rows": [
                {
                    "row_no": 1,
                    "order_no": "ORDER-HISTORY-DISPOSAL",
                    "return_tracking_no": "RTN-HISTORY-DISPOSAL",
                    "product_code": "P001",
                    "barcode": "880001",
                    "qty": 1,
                }
            ]
        },
    )
    _judge_processing_task(client, task_id=disposal_task_id, headers=disposal_headers, judgement_status="DISPOSAL")
    _mark_row_inventory_reflected_for_test(
        db_session,
        task_id=disposal_task_id,
        stock_status="DISPOSAL",
    )
    disposal_confirm = client.post(
        f"/api/returns/disposal/tasks/{disposal_task_id}/confirm",
        json={"disposal_reason": "테스트 폐기"},
        headers=disposal_headers,
    )

    response = client.get(f"/api/returns/history?client_id={client_row.id}&page_size=20", headers=outbound_headers)
    outbound_filter = client.get(
        "/api/returns/history?followup_status=EXTERNAL_OUTBOUND_CONFIRMED",
        headers=outbound_headers,
    )
    hold_filter = client.get("/api/returns/history?followup_status=READY_TO_REJUDGE", headers=hold_headers)
    disposal_filter = client.get(
        "/api/returns/history?followup_status=DISPOSAL_CONFIRMED",
        headers=disposal_headers,
    )

    assert outbound_confirm.status_code == 200
    assert disposal_confirm.status_code == 200
    assert response.status_code == 200
    items = {item["row_id"]: item for item in response.json()["data"]["items"]}
    assert items[outbound_task_id]["followup_status"] == "EXTERNAL_OUTBOUND_CONFIRMED"
    assert items[outbound_task_id]["external_outbound_status"] == "CONFIRMED"
    assert items[hold_task_id]["followup_status"] == "READY_TO_REJUDGE"
    assert items[hold_task_id]["hold_status"] == "READY_TO_REJUDGE"
    assert items[disposal_task_id]["followup_status"] == "DISPOSAL_CONFIRMED"
    assert items[disposal_task_id]["disposal_status"] == "DISPOSAL_CONFIRMED"
    assert outbound_filter.json()["data"]["total_count"] >= 1
    assert hold_filter.json()["data"]["total_count"] >= 1
    assert disposal_filter.json()["data"]["total_count"] >= 1
    _assert_no_sensitive_values(response.json())


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
    assert data["followup_rows"] == 0
    assert data["blocked_rows"] == 1
    assert data["row_results"][0]["result"] == "BLOCKED_AMBIGUOUS_GRADE"
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


def test_return_external_outbound_confirm_deducts_reflected_inventory(
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
    _mark_row_inventory_reflected_for_test(
        db_session,
        task_id=task_id,
        stock_status="MANUFACTURER_RETURN",
    )

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
    assert data["batch_id"] is not None
    assert data["batch_no"].startswith("EXOB-")
    assert data["row_results"][0]["external_outbound_batch_id"] == data["batch_id"]
    assert row.external_outbound_required is True
    assert row.external_outbound_status == "CONFIRMED"
    assert row.external_outbound_at is not None
    assert row.external_outbound_confirmed_by is not None
    assert row.external_outbound_batch_id == data["batch_id"]
    outbound_batch = db_session.query(ReturnExternalOutboundBatch).filter(ReturnExternalOutboundBatch.id == data["batch_id"]).one()
    assert outbound_batch.agency_id == client_row.agency_id
    assert outbound_batch.batch_no == data["batch_no"]
    assert outbound_batch.status == "CONFIRMED"
    assert outbound_batch.target_type == "NON_GOOD_EXTERNAL_OUTBOUND"
    assert outbound_batch.total_rows == 1
    assert outbound_batch.confirmed_rows == 1
    assert outbound_batch.confirmed_by is not None
    assert outbound_batch.confirmed_at is not None
    assert db_session.query(InventoryEvent).filter(InventoryEvent.event_type == "RETURN_EXTERNAL_OUTBOUND_OUT").count() == 1
    assert db_session.query(CurrentInventory).one().qty_on_hand == 0
    assert retry_response.status_code == 200
    retry_data = retry_response.json()["data"]
    assert retry_data["batch_id"] is None
    assert retry_data["confirmed_rows"] == 0
    assert retry_data["skipped_rows"] == 1


def test_return_external_outbound_batches_list_and_detail(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_outbound_batch_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_outbound_batch_admin",
        client_id=client_row.id,
    )
    judged = _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="REFURB_A")
    _mark_row_inventory_reflected_for_test(
        db_session,
        task_id=task_id,
        stock_status="REFURB_A",
    )

    confirm_response = client.post(
        "/api/returns/external-outbound/confirm",
        json={"row_ids": [task_id], "scanned_numbers": [judged["return_management_no"]]},
        headers=headers,
    )
    confirm_data = confirm_response.json()["data"]
    batch_id = confirm_data["batch_id"]

    list_response = client.get(
        f"/api/returns/external-outbound/batches?client_id={client_row.id}&keyword={confirm_data['batch_no']}",
        headers=headers,
    )
    detail_response = client.get(f"/api/returns/external-outbound/batches/{batch_id}", headers=headers)
    missing_response = client.get("/api/returns/external-outbound/batches/999999", headers=headers)
    no_auth_response = client.get("/api/returns/external-outbound/batches")

    assert confirm_response.status_code == 200
    assert list_response.status_code == 200
    list_data = list_response.json()["data"]
    assert list_data["total_count"] == 1
    assert list_data["items"][0]["batch_id"] == batch_id
    assert list_data["items"][0]["batch_no"] == confirm_data["batch_no"]
    assert list_data["items"][0]["agency_id"] == client_row.agency_id
    assert list_data["items"][0]["confirmed_rows"] == 1
    assert detail_response.status_code == 200
    detail_data = detail_response.json()["data"]
    assert detail_data["batch_id"] == batch_id
    assert detail_data["agency_id"] == client_row.agency_id
    assert detail_data["batch_no"] == confirm_data["batch_no"]
    assert detail_data["rows"][0]["row_id"] == task_id
    assert detail_data["rows"][0]["return_management_no"] == judged["return_management_no"]
    assert detail_data["rows"][0]["external_outbound_status"] == "CONFIRMED"
    assert missing_response.status_code == 404
    assert no_auth_response.status_code == 401
    _assert_no_sensitive_values(list_response.json())
    _assert_no_sensitive_values(detail_response.json())


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
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="REFURB_A")
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
    assert failed_confirm_response.json()["data"]["blocked_rows"] == 1
    assert failed_confirm_response.json()["data"]["row_results"][0]["result"] == "BLOCKED_INVALID_STATE"
    assert wrong_judgement_response.status_code == 200
    assert wrong_judgement_response.json()["data"]["blocked_rows"] == 1
    assert wrong_judgement_response.json()["data"]["row_results"][0]["result"] == "BLOCKED_INVALID_STATE"
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


def test_return_hold_rejudge_good_moves_to_closing_candidates(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, code="HOLD_REJUDGE_GOOD")
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_hold_rejudge_good_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_hold_ready_to_rejudge_task(
        client,
        db_session,
        login_id="return_hold_rejudge_good_admin",
        client_id=client_row.id,
    )

    response = client.post(
        f"/api/returns/hold/tasks/{task_id}/rejudge",
        json={"judgement_status": "GOOD", "judgement_memo": "rejudged as good"},
        headers=headers,
    )
    candidates_response = client.get("/api/returns/closing/candidates", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["judgement_status"] == "GOOD"
    assert data["hold_status"] == "RESOLVED"
    assert data["label_print_required"] is False
    assert data["label_print_status"] == "NOT_REQUIRED"
    assert data["inventory_reflected_yn"] is False
    assert candidates_response.status_code == 200
    assert candidates_response.json()["data"]["total_count"] == 1
    _assert_no_sensitive_values(response.json())


@pytest.mark.parametrize("judgement_status", ["REFURB", "SAMPLE", "MANUFACTURER_RETURN"])
def test_return_hold_rejudge_tracked_status_moves_to_external_outbound_candidates(
    client: TestClient,
    db_session: Session,
    judgement_status: str,
):
    client_row = _create_client(db_session, code=f"HOLD_REJUDGE_{judgement_status}")
    _create_product(db_session, client_row.id)
    login_id = f"return_hold_rejudge_{judgement_status.lower()}"
    _create_user(
        db_session,
        login_id=login_id,
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_hold_ready_to_rejudge_task(
        client,
        db_session,
        login_id=login_id,
        client_id=client_row.id,
    )

    response = client.post(
        f"/api/returns/hold/tasks/{task_id}/rejudge",
        json={"judgement_status": judgement_status, "judgement_memo": "tracked followup"},
        headers=headers,
    )
    candidates_response = client.get("/api/returns/external-outbound/candidates", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["judgement_status"] == judgement_status
    assert data["hold_status"] == "RESOLVED"
    assert data["external_outbound_required"] is True
    assert data["external_outbound_status"] == "READY"
    assert data["return_management_no"]
    assert data["return_label_no"]
    assert data["label_print_required"] is True
    assert data["label_print_status"] == "LOCAL_AGENT_NOT_CONNECTED"
    assert candidates_response.status_code == 200
    assert candidates_response.json()["data"]["total_count"] == 1


def test_return_hold_rejudge_disposal_moves_to_disposal_candidates(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, code="HOLD_REJUDGE_DISPOSAL")
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_hold_rejudge_disposal_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_hold_ready_to_rejudge_task(
        client,
        db_session,
        login_id="return_hold_rejudge_disposal_admin",
        client_id=client_row.id,
    )

    response = client.post(
        f"/api/returns/hold/tasks/{task_id}/rejudge",
        json={"judgement_status": "DISPOSAL", "judgement_memo": "dispose after check"},
        headers=headers,
    )
    candidates_response = client.get("/api/returns/disposal/candidates", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["judgement_status"] == "DISPOSAL"
    assert data["hold_status"] == "RESOLVED"
    assert data["disposal_status"] == "DISPOSAL_PENDING"
    assert data["label_print_required"] is False
    assert candidates_response.status_code == 200
    assert candidates_response.json()["data"]["total_count"] == 1


def test_return_hold_rejudge_hold_keeps_hold_candidate(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, code="HOLD_REJUDGE_HOLD")
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_hold_rejudge_hold_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_hold_ready_to_rejudge_task(
        client,
        db_session,
        login_id="return_hold_rejudge_hold_admin",
        client_id=client_row.id,
    )

    response = client.post(
        f"/api/returns/hold/tasks/{task_id}/rejudge",
        json={"judgement_status": "HOLD", "judgement_memo": "keep hold"},
        headers=headers,
    )
    candidates_response = client.get("/api/returns/hold/candidates", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["judgement_status"] == "HOLD"
    assert data["hold_status"] == "HOLD_PENDING"
    assert candidates_response.status_code == 200
    assert candidates_response.json()["data"]["total_count"] == 1


def test_return_hold_rejudge_blocks_invalid_conditions(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, code="HOLD_REJUDGE_BLOCK")
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_hold_rejudge_block_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, hold_task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_hold_rejudge_block_admin",
        client_id=client_row.id,
    )
    _judge_processing_task(client, task_id=hold_task_id, headers=headers, judgement_status="HOLD")
    not_ready_response = client.post(
        f"/api/returns/hold/tasks/{hold_task_id}/rejudge",
        json={"judgement_status": "GOOD"},
        headers=headers,
    )
    invalid_status_response = client.post(
        f"/api/returns/hold/tasks/{hold_task_id}/rejudge",
        json={"judgement_status": "UNKNOWN"},
        headers=headers,
    )

    headers_good, _batch_id_good, good_task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_hold_rejudge_block_admin",
        client_id=client_row.id,
    )
    _judge_processing_task(client, task_id=good_task_id, headers=headers_good, judgement_status="GOOD")
    non_hold_response = client.post(
        f"/api/returns/hold/tasks/{good_task_id}/rejudge",
        json={"judgement_status": "GOOD"},
        headers=headers_good,
    )

    headers_invalid, _batch_id_invalid, invalid_task_id = _prepare_hold_ready_to_rejudge_task(
        client,
        db_session,
        login_id="return_hold_rejudge_block_admin",
        client_id=client_row.id,
    )
    invalid_row = db_session.get(ReturnIntakeRow, invalid_task_id)
    assert invalid_row is not None
    invalid_row.validation_status = "INVALID"
    db_session.commit()
    invalid_validation_response = client.post(
        f"/api/returns/hold/tasks/{invalid_task_id}/rejudge",
        json={"judgement_status": "GOOD"},
        headers=headers_invalid,
    )
    missing_response = client.post(
        "/api/returns/hold/tasks/999999/rejudge",
        json={"judgement_status": "GOOD"},
        headers=headers,
    )

    assert not_ready_response.status_code == 400
    assert not_ready_response.json()["result_code"] == "RETURN_HOLD_REJUDGE_INVALID_HOLD_STATUS"
    assert invalid_status_response.status_code == 400
    assert invalid_status_response.json()["result_code"] == "RETURN_HOLD_REJUDGE_STATUS_INVALID"
    assert non_hold_response.status_code == 400
    assert non_hold_response.json()["result_code"] == "RETURN_HOLD_REJUDGE_INVALID_JUDGEMENT"
    assert invalid_validation_response.status_code == 400
    assert invalid_validation_response.json()["result_code"] == "RETURN_HOLD_REJUDGE_INVALID_VALIDATION"
    assert missing_response.status_code == 404
    assert missing_response.json()["result_code"] == "RETURN_HOLD_TASK_NOT_FOUND"


def test_return_disposal_candidates_include_disposal_completed_rows(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_disposal_candidates_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_disposal_candidates_admin",
        client_id=client_row.id,
    )
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="DISPOSAL")

    response = client.get("/api/returns/disposal/candidates", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_count"] == 1
    item = data["items"][0]
    assert item["row_id"] == task_id
    assert item["judgement_status"] == "DISPOSAL"
    assert item["disposal_status"] == "DISPOSAL_PENDING"
    _assert_no_sensitive_values(response.json())


@pytest.mark.parametrize("judgement_status", ["GOOD", "REFURB", "SAMPLE", "MANUFACTURER_RETURN", "HOLD"])
def test_return_disposal_candidates_exclude_non_disposal_judgements(
    client: TestClient,
    db_session: Session,
    judgement_status: str,
):
    client_row = _create_client(db_session, code=f"DISPOSAL_EXCLUDE_{judgement_status}")
    _create_product(db_session, client_row.id)
    login_id = f"return_disposal_exclude_{judgement_status.lower()}"
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

    response = client.get("/api/returns/disposal/candidates", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["total_count"] == 0


def test_return_disposal_confirm_deducts_reflected_inventory_and_saves_reason_memo(
    client: TestClient,
    db_session: Session,
):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_disposal_confirm_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_disposal_confirm_admin",
        client_id=client_row.id,
    )
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="DISPOSAL")
    _mark_row_inventory_reflected_for_test(
        db_session,
        task_id=task_id,
        stock_status="DISPOSAL",
    )

    response = client.post(
        f"/api/returns/disposal/tasks/{task_id}/confirm",
        json={"disposal_reason": "파손 폐기", "disposal_memo": "작업자 확인 후 폐기"},
        headers=headers,
    )
    candidates_response = client.get("/api/returns/disposal/candidates", headers=headers)
    row = db_session.get(ReturnIntakeRow, task_id)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["disposal_status"] == "DISPOSAL_CONFIRMED"
    assert data["disposal_reason"] == "파손 폐기"
    assert data["disposal_memo"] == "작업자 확인 후 폐기"
    assert data["disposal_confirmed_at"] is not None
    assert row is not None
    assert row.disposal_status == "DISPOSAL_CONFIRMED"
    assert row.disposal_confirmed_at is not None
    assert row.disposal_confirmed_by is not None
    assert db_session.query(CurrentInventory).one().qty_on_hand == 0
    deduction_event = (
        db_session.query(InventoryEvent)
        .filter(InventoryEvent.event_type == "RETURN_DISPOSAL_OUT")
        .one()
    )
    assert deduction_event.qty_delta == -(row.qty or 1)
    assert candidates_response.status_code == 200
    assert candidates_response.json()["data"]["total_count"] == 0


def test_return_disposal_confirm_blocks_already_confirmed_non_disposal_and_missing_task(
    client: TestClient,
    db_session: Session,
):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_disposal_block_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_disposal_block_admin",
        client_id=client_row.id,
    )
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="DISPOSAL")
    _mark_row_inventory_reflected_for_test(
        db_session,
        task_id=task_id,
        stock_status="DISPOSAL",
    )
    first_response = client.post(
        f"/api/returns/disposal/tasks/{task_id}/confirm",
        json={"disposal_reason": "폐기"},
        headers=headers,
    )
    retry_response = client.post(
        f"/api/returns/disposal/tasks/{task_id}/confirm",
        json={"disposal_reason": "재확정"},
        headers=headers,
    )

    headers_good, _batch_id_good, good_task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_disposal_block_admin",
        client_id=client_row.id,
    )
    _judge_processing_task(client, task_id=good_task_id, headers=headers_good, judgement_status="GOOD")
    non_disposal_response = client.post(
        f"/api/returns/disposal/tasks/{good_task_id}/confirm",
        json={"disposal_reason": "폐기"},
        headers=headers_good,
    )
    missing_response = client.post(
        "/api/returns/disposal/tasks/999999/confirm",
        json={"disposal_reason": "폐기"},
        headers=headers,
    )

    assert first_response.status_code == 200
    assert retry_response.status_code == 400
    assert retry_response.json()["result_code"] == "RETURN_DISPOSAL_ALREADY_CONFIRMED"
    assert non_disposal_response.status_code == 400
    assert non_disposal_response.json()["result_code"] == "RETURN_DISPOSAL_INVALID_JUDGEMENT"
    assert missing_response.status_code == 404
    assert missing_response.json()["result_code"] == "RETURN_DISPOSAL_TASK_NOT_FOUND"


def test_return_processing_judge_good_fails_without_warehouse_setting(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    product = Product(
        client_id=client_row.id,
        product_code="NO-WH-P001",
        product_name="No Warehouse Product",
        barcode="NO-WH-BC001",
        active_yn=True,
    )
    db_session.add(product)
    db_session.commit()
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
        rows_payload={
            "rows": [
                {
                    "row_no": 1,
                    "order_no": "ORDER-NO-WH",
                    "return_tracking_no": "RTN-NO-WH",
                    "product_code": product.product_code,
                    "barcode": product.barcode,
                    "qty": 1,
                }
            ]
        },
    )
    response = client.post(
        f"/api/returns/processing/tasks/{task_id}/judge",
        json={"judgement_status": "GOOD"},
        headers=headers,
    )
    row = db_session.query(ReturnIntakeRow).filter(ReturnIntakeRow.id == task_id).one()

    assert response.status_code == 400
    assert response.json()["result_code"] == "RETURN_PROCESSING_WAREHOUSE_REQUIRED"
    assert row.status == "READY_FOR_PROCESSING"
    assert row.inventory_reflected_yn is False
    assert db_session.query(InventoryEvent).count() == 0


def test_return_processing_judge_good_fails_without_product(client: TestClient, db_session: Session):
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
    response = client.post(
        f"/api/returns/processing/tasks/{task_id}/judge",
        json={"judgement_status": "GOOD"},
        headers=headers,
    )
    row = db_session.query(ReturnIntakeRow).filter(ReturnIntakeRow.id == task_id).one()

    assert response.status_code == 400
    assert response.json()["result_code"] == "RETURN_PROCESSING_PRODUCT_NOT_FOUND"
    assert row.status == "READY_FOR_PROCESSING"
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


def test_external_outbound_target_followup_includes_refurb_grades(
    client: TestClient,
    db_session: Session,
):
    # 외부반출 후보(history followup)가 generic REFURB뿐 아니라 REFURB_A/B/C도 포함해야 한다.
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_outbound_target_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_outbound_target_admin",
        client_id=client_row.id,
        rows_payload={
            "rows": [
                {
                    "row_no": 1,
                    "order_no": "ORDER-OUT-TARGET",
                    "return_tracking_no": "RTN-OUT-TARGET",
                    "product_code": "P001",
                    "barcode": "880001",
                    "qty": 1,
                }
            ]
        },
    )
    _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="REFURB_A")

    filtered = client.get(
        f"/api/returns/history?client_id={client_row.id}&followup_status=EXTERNAL_OUTBOUND_TARGET&page_size=50",
        headers=headers,
    )
    assert filtered.status_code == 200
    row_ids = {item["row_id"] for item in filtered.json()["data"]["items"]}
    assert task_id in row_ids


def test_defective_judgement_completes_with_client_warehouse_route(
    client: TestClient,
    db_session: Session,
):
    # DEFECTIVE 판정이 ALLOWED + 고객사 창고 라우팅으로 처리완료되어야 한다(기본 창고 하드코딩 없이).
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    defective_warehouse = _create_warehouse_setting(
        db_session,
        client_id=client_row.id,
        usage_type="RETURN_ROUTE_DEFECTIVE",
    )
    _create_return_warehouse_route(
        db_session,
        client_id=client_row.id,
        warehouse_id=defective_warehouse.id,
        judgement_code="DEFECTIVE",
    )
    _create_user(
        db_session,
        login_id="return_defective_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_defective_admin",
        client_id=client_row.id,
        rows_payload={
            "rows": [
                {
                    "row_no": 1,
                    "order_no": "ORDER-DEFECTIVE",
                    "return_tracking_no": "RTN-DEFECTIVE",
                    "product_code": "P001",
                    "barcode": "880001",
                    "qty": 1,
                }
            ]
        },
    )
    judged = _judge_processing_task(client, task_id=task_id, headers=headers, judgement_status="DEFECTIVE")
    assert judged["judgement_status"] == "DEFECTIVE"
    assert judged["status"] == "COMPLETED"
    # DEFECTIVE는 라벨 대상으로 반품관리번호가 생성된다.
    assert judged["return_management_no"]


def test_defective_judgement_blocked_without_warehouse_route(
    client: TestClient,
    db_session: Session,
):
    # DEFECTIVE 창고 라우팅이 없으면 처리완료가 막혀야 한다(기본 창고를 하드코딩하지 않는다).
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id)
    _create_user(
        db_session,
        login_id="return_defective_norote_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_return_permissions(),
    )
    headers, _batch_id, task_id = _prepare_processing_task(
        client,
        db_session,
        login_id="return_defective_norote_admin",
        client_id=client_row.id,
        rows_payload={
            "rows": [
                {
                    "row_no": 1,
                    "order_no": "ORDER-DEFECTIVE-NOROUTE",
                    "return_tracking_no": "RTN-DEFECTIVE-NOROUTE",
                    "product_code": "P001",
                    "barcode": "880001",
                    "qty": 1,
                }
            ]
        },
    )
    response = client.post(
        f"/api/returns/processing/tasks/{task_id}/judge",
        json={"judgement_status": "DEFECTIVE"},
        headers=headers,
    )
    assert response.status_code != 200
