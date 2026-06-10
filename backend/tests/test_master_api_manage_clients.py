from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.auth import Permission, Role, RolePermission, User, UserRole
from app.models.master import Agency, Client, ClientUnit, ClientWarehouseSetting, ReturnJudgmentWarehouseRoute, Warehouse


TEST_PASSWORD = "DummyPass123!"


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
        ClientWarehouseSetting.__table__,
        ReturnJudgmentWarehouseRoute.__table__,
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


def _create_client(db: Session, code: str = "CLIENT_A", name: str = "Test Client") -> Client:
    agency = Agency(agency_code=f"AGENCY_{code}", agency_name=f"{name} Agency", active_yn=True)
    client = Client(client_code=code, client_name=name, agency_id=None, active_yn=True)
    db.add_all([agency, client])
    db.flush()
    client.agency_id = agency.id
    db.commit()
    return client


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
            permission = Permission(
                permission_code=permission_code,
                permission_name=permission_code,
                active_yn=True,
            )
            db.add(permission)
            db.flush()
        db.add(RolePermission(role_id=role.id, permission_id=permission.id))

    db.commit()
    return user


def _login(client: TestClient, login_id: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"login_id": login_id, "password": TEST_PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _manage_permissions() -> list[str]:
    return ["MASTER_MANAGE", "CLIENT_MANAGE"]


def _warehouse_manage_permissions() -> list[str]:
    return ["MASTER_VIEW", "MASTER_MANAGE", "WAREHOUSE_MANAGE"]


def _create_client_warehouse_setting(db: Session, client_id: int, warehouse_id: int) -> ClientWarehouseSetting:
    setting = ClientWarehouseSetting(
        agency_id=db.get(Client, client_id).agency_id if db.get(Client, client_id) is not None else None,
        client_id=client_id,
        warehouse_id=warehouse_id,
        usage_type="RETURN_GOOD",
        is_default=True,
        active_yn=True,
    )
    db.add(setting)
    db.commit()
    return setting


def _client_payload(**overrides) -> dict:
    payload = {
        "client_code": "CLIENT_NEW",
        "client_name": "New Client",
        "business_no": "000-00-00000",
        "contact_name": "Tester",
        "contact_phone": "010-0000-0000",
        "contact_email": "test@example.com",
        "use_oms": False,
        "use_wms": True,
        "use_returns": True,
        "use_settlement": False,
        "remarks": "test",
    }
    payload.update(overrides)
    return payload


def _assert_no_sensitive_values(data: dict) -> None:
    text = str(data).lower()
    for value in ("password", "secret", "token", "hash"):
        assert value not in text


def test_client_manage_requires_auth(client: TestClient):
    response = client.post("/api/master/clients", json=_client_payload())

    assert response.status_code == 401
    assert response.json()["result_code"] == "NOT_AUTHENTICATED"


@pytest.mark.parametrize("role_code", ["READ_ONLY", "CLIENT_ADMIN", "INTERNAL_WORKER"])
def test_client_manage_blocks_roles_without_manage_permission(
    client: TestClient,
    db_session: Session,
    role_code: str,
):
    user_client_id = _create_client(db_session).id if role_code in {"READ_ONLY", "CLIENT_ADMIN"} else None
    _create_user(
        db_session,
        login_id=f"blocked_client_{role_code.lower()}",
        role_code=role_code,
        permissions=["MASTER_VIEW"],
        client_id=user_client_id,
    )

    response = client.post(
        "/api/master/clients",
        json=_client_payload(),
        headers=_login(client, f"blocked_client_{role_code.lower()}"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "PERMISSION_DENIED"


def test_internal_admin_can_create_client(client: TestClient, db_session: Session):
    _create_user(
        db_session,
        login_id="client_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )

    response = client.post(
        "/api/master/clients",
        json=_client_payload(),
        headers=_login(client, "client_admin"),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["result_code"] == "MASTER_CLIENT_CREATED"
    assert data["data"]["client_code"] == "CLIENT_NEW"
    assert data["data"]["use_wms"] is True
    _assert_no_sensitive_values(data)


def test_client_create_blocks_duplicate_client_code(client: TestClient, db_session: Session):
    _create_client(db_session, code="CLIENT_DUP")
    _create_user(
        db_session,
        login_id="duplicate_client_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )

    response = client.post(
        "/api/master/clients",
        json=_client_payload(client_code="CLIENT_DUP", client_name="Duplicate Name"),
        headers=_login(client, "duplicate_client_admin"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "MASTER_CLIENT_CODE_DUPLICATED"


def test_client_unit_crud_flow(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, code="CLIENT_UNIT")
    _create_user(
        db_session,
        login_id="client_unit_admin",
        role_code="INTERNAL_ADMIN",
        permissions=["MASTER_VIEW", *_manage_permissions()],
    )
    headers = _login(client, "client_unit_admin")

    create_response = client.post(
        f"/api/master/clients/{client_row.id}/units",
        json={"unit_code": "ONLINE", "unit_name": "온라인팀", "unit_type": "TEAM", "sort_order": 1},
        headers=headers,
    )
    assert create_response.status_code == 200
    unit_id = create_response.json()["data"]["unit_id"]

    list_response = client.get(f"/api/master/clients/{client_row.id}/units", headers=headers)
    update_response = client.patch(
        f"/api/master/clients/{client_row.id}/units/{unit_id}",
        json={"unit_name": "온라인운영팀", "memo": "test"},
        headers=headers,
    )
    disable_response = client.post(f"/api/master/clients/{client_row.id}/units/{unit_id}/disable", headers=headers)
    enable_response = client.post(f"/api/master/clients/{client_row.id}/units/{unit_id}/enable", headers=headers)

    assert list_response.status_code == 200
    assert list_response.json()["data"][0]["unit_code"] == "ONLINE"
    assert update_response.status_code == 200
    assert update_response.json()["data"]["unit_name"] == "온라인운영팀"
    assert disable_response.status_code == 200
    assert disable_response.json()["data"]["active_yn"] is False
    assert enable_response.status_code == 200
    assert enable_response.json()["data"]["active_yn"] is True
    _assert_no_sensitive_values(enable_response.json())


def test_client_unit_blocks_duplicate_code_in_same_client(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, code="CLIENT_UNIT_DUP")
    db_session.add(ClientUnit(client_id=client_row.id, unit_code="ONLINE", unit_name="온라인팀", active_yn=True))
    db_session.commit()
    _create_user(
        db_session,
        login_id="client_unit_dup_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )

    response = client.post(
        f"/api/master/clients/{client_row.id}/units",
        json={"unit_code": "ONLINE", "unit_name": "중복팀"},
        headers=_login(client, "client_unit_dup_admin"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "MASTER_CLIENT_UNIT_CODE_DUPLICATED"


def test_client_unit_blocks_warehouse_from_other_client(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, code="CLIENT_UNIT_SCOPE")
    other_client = _create_client(db_session, code="CLIENT_UNIT_OTHER")
    other_warehouse = Warehouse(warehouse_code="OTHER-WH", warehouse_name="Other Warehouse", active_yn=True)
    db_session.add(other_warehouse)
    db_session.flush()
    _create_client_warehouse_setting(db_session, client_id=other_client.id, warehouse_id=other_warehouse.id)
    _create_user(
        db_session,
        login_id="client_unit_scope_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )

    response = client.post(
        f"/api/master/clients/{client_row.id}/units",
        json={
            "unit_code": "SCOPE",
            "unit_name": "범위검증팀",
            "default_warehouse_id": other_warehouse.id,
        },
        headers=_login(client, "client_unit_scope_admin"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "MASTER_CLIENT_UNIT_WAREHOUSE_UNLINKED"


def test_return_warehouse_route_crud_flow(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, code="CLIENT_ROUTE")
    warehouse = Warehouse(warehouse_code="ROUTE-WH", warehouse_name="Route Warehouse", active_yn=True)
    db_session.add(warehouse)
    db_session.flush()
    _create_client_warehouse_setting(db_session, client_id=client_row.id, warehouse_id=warehouse.id)
    unit = ClientUnit(client_id=client_row.id, unit_code="ONLINE", unit_name="온라인팀", active_yn=True)
    db_session.add(unit)
    db_session.commit()
    _create_user(
        db_session,
        login_id="route_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_warehouse_manage_permissions(),
    )
    headers = _login(client, "route_admin")

    create_response = client.post(
        f"/api/master/clients/{client_row.id}/return-warehouse-routes",
        json={
            "client_unit_id": unit.id,
            "judgment_code": "GOOD",
            "warehouse_id": warehouse.id,
            "sort_order": 1,
            "memo": "route",
        },
        headers=headers,
    )
    assert create_response.status_code == 200
    route_id = create_response.json()["data"]["route_id"]

    list_response = client.get(f"/api/master/clients/{client_row.id}/return-warehouse-routes", headers=headers)
    update_response = client.patch(
        f"/api/master/clients/{client_row.id}/return-warehouse-routes/{route_id}",
        json={"sort_order": 5, "memo": "updated"},
        headers=headers,
    )
    disable_response = client.post(
        f"/api/master/clients/{client_row.id}/return-warehouse-routes/{route_id}/disable",
        headers=headers,
    )
    enable_response = client.post(
        f"/api/master/clients/{client_row.id}/return-warehouse-routes/{route_id}/enable",
        headers=headers,
    )

    assert list_response.status_code == 200
    assert list_response.json()["data"][0]["route_id"] == route_id
    assert update_response.status_code == 200
    assert update_response.json()["data"]["sort_order"] == 5
    assert disable_response.status_code == 200
    assert disable_response.json()["data"]["active_yn"] is False
    assert enable_response.status_code == 200
    assert enable_response.json()["data"]["active_yn"] is True
    _assert_no_sensitive_values(enable_response.json())


def test_return_warehouse_route_blocks_duplicate_and_foreign_scope(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, code="CLIENT_ROUTE_SCOPE")
    other_client = _create_client(db_session, code="CLIENT_ROUTE_OTHER")
    warehouse = Warehouse(warehouse_code="ROUTE-SCOPE-WH", warehouse_name="Route Scope Warehouse", active_yn=True)
    other_warehouse = Warehouse(warehouse_code="OTHER-WH", warehouse_name="Other Warehouse", active_yn=True)
    db_session.add_all([warehouse, other_warehouse])
    db_session.flush()
    _create_client_warehouse_setting(db_session, client_id=client_row.id, warehouse_id=warehouse.id)
    _create_client_warehouse_setting(db_session, client_id=other_client.id, warehouse_id=other_warehouse.id)
    unit = ClientUnit(client_id=client_row.id, unit_code="ONLINE", unit_name="온라인팀", active_yn=True)
    other_unit = ClientUnit(client_id=other_client.id, unit_code="OTHER", unit_name="다른팀", active_yn=True)
    db_session.add_all([unit, other_unit])
    db_session.commit()
    _create_user(
        db_session,
        login_id="route_scope_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_warehouse_manage_permissions(),
    )
    headers = _login(client, "route_scope_admin")

    ok_response = client.post(
        f"/api/master/clients/{client_row.id}/return-warehouse-routes",
        json={"client_unit_id": unit.id, "judgment_code": "GOOD", "warehouse_id": warehouse.id},
        headers=headers,
    )
    duplicate_response = client.post(
        f"/api/master/clients/{client_row.id}/return-warehouse-routes",
        json={"client_unit_id": unit.id, "judgment_code": "GOOD", "warehouse_id": warehouse.id},
        headers=headers,
    )
    foreign_unit_response = client.post(
        f"/api/master/clients/{client_row.id}/return-warehouse-routes",
        json={"client_unit_id": other_unit.id, "judgment_code": "SAMPLE", "warehouse_id": warehouse.id},
        headers=headers,
    )
    foreign_warehouse_response = client.post(
        f"/api/master/clients/{client_row.id}/return-warehouse-routes",
        json={"client_unit_id": unit.id, "judgment_code": "SAMPLE", "warehouse_id": other_warehouse.id},
        headers=headers,
    )

    assert ok_response.status_code == 200
    assert duplicate_response.status_code == 400
    assert duplicate_response.json()["result_code"] == "MASTER_RETURN_WAREHOUSE_ROUTE_DUPLICATED"
    assert foreign_unit_response.status_code == 404
    assert foreign_unit_response.json()["result_code"] == "MASTER_RETURN_WAREHOUSE_ROUTE_UNIT_INVALID"
    assert foreign_warehouse_response.status_code == 400
    assert foreign_warehouse_response.json()["result_code"] == "MASTER_RETURN_WAREHOUSE_ROUTE_WAREHOUSE_UNLINKED"


def test_client_update_does_not_change_client_code(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, code="CLIENT_KEEP")
    _create_user(
        db_session,
        login_id="client_update_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )

    response = client.patch(
        f"/api/master/clients/{client_row.id}",
        json={"client_code": "CLIENT_CHANGED", "client_name": "Updated Client", "remarks": "updated"},
        headers=_login(client, "client_update_admin"),
    )
    db_session.refresh(client_row)

    assert response.status_code == 200
    assert response.json()["result_code"] == "MASTER_CLIENT_UPDATED"
    assert response.json()["data"]["client_name"] == "Updated Client"
    assert client_row.client_code == "CLIENT_KEEP"


def test_client_disable_enable(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_user(
        db_session,
        login_id="client_active_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )
    headers = _login(client, "client_active_admin")

    disable_response = client.post(f"/api/master/clients/{client_row.id}/disable", headers=headers)
    enable_response = client.post(f"/api/master/clients/{client_row.id}/enable", headers=headers)

    assert disable_response.status_code == 200
    assert disable_response.json()["result_code"] == "MASTER_CLIENT_DISABLED"
    assert disable_response.json()["data"]["active_yn"] is False
    assert enable_response.status_code == 200
    assert enable_response.json()["result_code"] == "MASTER_CLIENT_ENABLED"
    assert enable_response.json()["data"]["active_yn"] is True
