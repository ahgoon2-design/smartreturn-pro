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
from app.models.master import Client, ClientWarehouseSetting, Warehouse


TEST_PASSWORD = "DummyPass123!"


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
        ClientWarehouseSetting.__table__,
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
    client = Client(client_code=code, client_name=f"{code} Name", active_yn=active_yn)
    db.add(client)
    db.commit()
    return client


def _create_warehouse(db: Session, code: str = "WH_A", active_yn: bool = True) -> Warehouse:
    warehouse = Warehouse(warehouse_code=code, warehouse_name=f"{code} Name", active_yn=active_yn)
    db.add(warehouse)
    db.commit()
    return warehouse


def _create_setting(
    db: Session,
    *,
    client_id: int,
    warehouse_id: int,
    usage_type: str = "RETURN_GOOD",
    is_default: bool = False,
    active_yn: bool = True,
) -> ClientWarehouseSetting:
    setting = ClientWarehouseSetting(
        client_id=client_id,
        warehouse_id=warehouse_id,
        usage_type=usage_type,
        is_default=is_default,
        active_yn=active_yn,
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
    return ["MASTER_MANAGE", "WAREHOUSE_MANAGE"]


def _payload(client_id: int, warehouse_id: int, **overrides) -> dict:
    payload = {
        "client_id": client_id,
        "warehouse_id": warehouse_id,
        "usage_type": "RETURN_GOOD",
        "is_default": False,
    }
    payload.update(overrides)
    return payload


def _assert_no_sensitive_values(data: dict) -> None:
    text = str(data).lower()
    for value in ("password", "secret", "token", "hash"):
        assert value not in text


def test_client_warehouse_manage_requires_auth(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    warehouse = _create_warehouse(db_session)

    response = client.post("/api/master/client-warehouses", json=_payload(client_row.id, warehouse.id))

    assert response.status_code == 401
    assert response.json()["result_code"] == "NOT_AUTHENTICATED"


@pytest.mark.parametrize("role_code", ["READ_ONLY", "CLIENT_ADMIN", "INTERNAL_WORKER"])
def test_client_warehouse_manage_blocks_roles_without_manage_permission(
    client: TestClient,
    db_session: Session,
    role_code: str,
):
    client_row = _create_client(db_session)
    warehouse = _create_warehouse(db_session)
    user_client_id = client_row.id if role_code in {"READ_ONLY", "CLIENT_ADMIN"} else None
    _create_user(
        db_session,
        login_id=f"blocked_cw_{role_code.lower()}",
        role_code=role_code,
        permissions=["MASTER_VIEW"],
        client_id=user_client_id,
    )

    response = client.post(
        "/api/master/client-warehouses",
        json=_payload(client_row.id, warehouse.id),
        headers=_login(client, f"blocked_cw_{role_code.lower()}"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "PERMISSION_DENIED"


def test_internal_admin_can_create_client_warehouse_setting(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    warehouse = _create_warehouse(db_session)
    _create_user(
        db_session,
        login_id="cw_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )

    response = client.post(
        "/api/master/client-warehouses",
        json=_payload(client_row.id, warehouse.id, is_default=True),
        headers=_login(client, "cw_admin"),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["result_code"] == "MASTER_CLIENT_WAREHOUSE_CREATED"
    assert data["data"]["setting_id"] > 0
    assert data["data"]["client_id"] == client_row.id
    assert data["data"]["warehouse_id"] == warehouse.id
    assert data["data"]["usage_type"] == "RETURN_GOOD"
    assert data["data"]["is_default"] is True
    _assert_no_sensitive_values(data)


def test_client_warehouse_create_blocks_inactive_client(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, active_yn=False)
    warehouse = _create_warehouse(db_session)
    _create_user(db_session, login_id="cw_inactive_client", role_code="INTERNAL_ADMIN", permissions=_manage_permissions())

    response = client.post(
        "/api/master/client-warehouses",
        json=_payload(client_row.id, warehouse.id),
        headers=_login(client, "cw_inactive_client"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "MASTER_CLIENT_INACTIVE"


def test_client_warehouse_create_blocks_inactive_warehouse(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    warehouse = _create_warehouse(db_session, active_yn=False)
    _create_user(db_session, login_id="cw_inactive_wh", role_code="INTERNAL_ADMIN", permissions=_manage_permissions())

    response = client.post(
        "/api/master/client-warehouses",
        json=_payload(client_row.id, warehouse.id),
        headers=_login(client, "cw_inactive_wh"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "MASTER_WAREHOUSE_INACTIVE"


def test_client_warehouse_create_blocks_duplicate_usage(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    warehouse = _create_warehouse(db_session)
    _create_setting(db_session, client_id=client_row.id, warehouse_id=warehouse.id, active_yn=False)
    _create_user(db_session, login_id="cw_duplicate", role_code="INTERNAL_ADMIN", permissions=_manage_permissions())

    response = client.post(
        "/api/master/client-warehouses",
        json=_payload(client_row.id, warehouse.id),
        headers=_login(client, "cw_duplicate"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "MASTER_CLIENT_WAREHOUSE_DUPLICATED"


def test_client_warehouse_update_succeeds(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    warehouse = _create_warehouse(db_session)
    setting = _create_setting(db_session, client_id=client_row.id, warehouse_id=warehouse.id, usage_type="RETURN_GOOD")
    _create_user(db_session, login_id="cw_update", role_code="INTERNAL_ADMIN", permissions=_manage_permissions())

    response = client.patch(
        f"/api/master/client-warehouses/{setting.id}",
        json={"usage_type": "STORAGE"},
        headers=_login(client, "cw_update"),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["result_code"] == "MASTER_CLIENT_WAREHOUSE_UPDATED"
    assert data["data"]["usage_type"] == "STORAGE"


def test_default_client_warehouse_blocks_usage_type_change(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    warehouse = _create_warehouse(db_session)
    setting = _create_setting(
        db_session,
        client_id=client_row.id,
        warehouse_id=warehouse.id,
        usage_type="RETURN_GOOD",
        is_default=True,
    )
    _create_user(db_session, login_id="cw_default_update", role_code="INTERNAL_ADMIN", permissions=_manage_permissions())

    response = client.patch(
        f"/api/master/client-warehouses/{setting.id}",
        json={"usage_type": "STORAGE"},
        headers=_login(client, "cw_default_update"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "MASTER_CLIENT_WAREHOUSE_DEFAULT_USAGE_TYPE_LOCKED"


def test_create_default_unsets_existing_default(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    warehouse_a = _create_warehouse(db_session, code="WH_A")
    warehouse_b = _create_warehouse(db_session, code="WH_B")
    existing = _create_setting(
        db_session,
        client_id=client_row.id,
        warehouse_id=warehouse_a.id,
        usage_type="RETURN_GOOD",
        is_default=True,
    )
    _create_user(db_session, login_id="cw_create_default", role_code="INTERNAL_ADMIN", permissions=_manage_permissions())

    response = client.post(
        "/api/master/client-warehouses",
        json=_payload(client_row.id, warehouse_b.id, is_default=True),
        headers=_login(client, "cw_create_default"),
    )

    assert response.status_code == 200
    db_session.refresh(existing)
    assert existing.is_default is False
    assert response.json()["data"]["is_default"] is True


def test_set_default_unsets_existing_default(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    warehouse_a = _create_warehouse(db_session, code="WH_A")
    warehouse_b = _create_warehouse(db_session, code="WH_B")
    old_default = _create_setting(
        db_session,
        client_id=client_row.id,
        warehouse_id=warehouse_a.id,
        usage_type="RETURN_GOOD",
        is_default=True,
    )
    new_default = _create_setting(
        db_session,
        client_id=client_row.id,
        warehouse_id=warehouse_b.id,
        usage_type="RETURN_GOOD",
        is_default=False,
    )
    _create_user(db_session, login_id="cw_set_default", role_code="INTERNAL_ADMIN", permissions=_manage_permissions())

    response = client.post(
        f"/api/master/client-warehouses/{new_default.id}/set-default",
        headers=_login(client, "cw_set_default"),
    )

    assert response.status_code == 200
    assert response.json()["result_code"] == "MASTER_CLIENT_WAREHOUSE_DEFAULT_SET"
    db_session.refresh(old_default)
    db_session.refresh(new_default)
    assert old_default.is_default is False
    assert new_default.is_default is True


def test_default_client_warehouse_disable_is_blocked(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    warehouse = _create_warehouse(db_session)
    setting = _create_setting(db_session, client_id=client_row.id, warehouse_id=warehouse.id, is_default=True)
    _create_user(db_session, login_id="cw_disable_default", role_code="INTERNAL_ADMIN", permissions=_manage_permissions())

    response = client.post(
        f"/api/master/client-warehouses/{setting.id}/disable",
        headers=_login(client, "cw_disable_default"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "MASTER_CLIENT_WAREHOUSE_DEFAULT_DISABLE_DENIED"


def test_non_default_client_warehouse_disable_and_enable(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    warehouse = _create_warehouse(db_session)
    setting = _create_setting(db_session, client_id=client_row.id, warehouse_id=warehouse.id, is_default=False)
    _create_user(db_session, login_id="cw_active", role_code="INTERNAL_ADMIN", permissions=_manage_permissions())
    headers = _login(client, "cw_active")

    disable_response = client.post(f"/api/master/client-warehouses/{setting.id}/disable", headers=headers)

    assert disable_response.status_code == 200
    assert disable_response.json()["result_code"] == "MASTER_CLIENT_WAREHOUSE_DISABLED"
    assert disable_response.json()["data"]["active_yn"] is False

    enable_response = client.post(f"/api/master/client-warehouses/{setting.id}/enable", headers=headers)

    assert enable_response.status_code == 200
    assert enable_response.json()["result_code"] == "MASTER_CLIENT_WAREHOUSE_ENABLED"
    assert enable_response.json()["data"]["active_yn"] is True
    assert enable_response.json()["data"]["is_default"] is False


def test_readonly_client_warehouses_still_returns_active_settings(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    warehouse_active = _create_warehouse(db_session, code="WH_ACTIVE")
    warehouse_inactive_setting = _create_warehouse(db_session, code="WH_INACTIVE_SETTING")
    _create_setting(
        db_session,
        client_id=client_row.id,
        warehouse_id=warehouse_active.id,
        usage_type="RETURN_GOOD",
        is_default=True,
        active_yn=True,
    )
    _create_setting(
        db_session,
        client_id=client_row.id,
        warehouse_id=warehouse_inactive_setting.id,
        usage_type="STORAGE",
        is_default=False,
        active_yn=False,
    )
    _create_user(
        db_session,
        login_id="cw_readonly",
        role_code="INTERNAL_ADMIN",
        permissions=["MASTER_VIEW"],
    )

    response = client.get(
        f"/api/master/client-warehouses?client_id={client_row.id}",
        headers=_login(client, "cw_readonly"),
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["warehouse_id"] == warehouse_active.id
    assert data[0]["usage_type"] == "RETURN_GOOD"


def test_nested_client_warehouse_settings_returns_screen_fields(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    warehouse_active = _create_warehouse(db_session, code="WH_ACTIVE")
    warehouse_inactive_setting = _create_warehouse(db_session, code="WH_INACTIVE_SETTING")
    active_setting = _create_setting(
        db_session,
        client_id=client_row.id,
        warehouse_id=warehouse_active.id,
        usage_type="RETURN_GOOD",
        is_default=True,
        active_yn=True,
    )
    inactive_setting = _create_setting(
        db_session,
        client_id=client_row.id,
        warehouse_id=warehouse_inactive_setting.id,
        usage_type="STORAGE",
        is_default=False,
        active_yn=False,
    )
    _create_user(
        db_session,
        login_id="cw_nested_list",
        role_code="INTERNAL_ADMIN",
        permissions=["MASTER_VIEW"],
    )
    headers = _login(client, "cw_nested_list")

    active_response = client.get(f"/api/master/clients/{client_row.id}/warehouse-settings", headers=headers)
    inactive_response = client.get(
        f"/api/master/clients/{client_row.id}/warehouse-settings?include_inactive=true",
        headers=headers,
    )

    assert active_response.status_code == 200
    data = active_response.json()
    assert data["result_code"] == "MASTER_CLIENT_WAREHOUSE_SETTINGS_FOUND"
    assert len(data["data"]) == 1
    row = data["data"][0]
    assert row["setting_id"] == active_setting.id
    assert row["client_id"] == client_row.id
    assert row["client_code"] == client_row.client_code
    assert row["warehouse_id"] == warehouse_active.id
    assert row["warehouse_code"] == warehouse_active.warehouse_code
    assert row["usage_type_label"] == "반품양품"
    assert row["warehouse_active_yn"] is True
    assert row["allowed_actions"] == {
        "can_update": False,
        "can_disable": False,
        "can_enable": False,
        "can_set_default": False,
    }
    assert inactive_response.status_code == 200
    rows = inactive_response.json()["data"]
    assert {item["setting_id"] for item in rows} == {active_setting.id, inactive_setting.id}
    _assert_no_sensitive_values(data)


def test_client_user_nested_warehouse_settings_are_scoped(client: TestClient, db_session: Session):
    client_a = _create_client(db_session, code="CLIENT_A")
    client_b = _create_client(db_session, code="CLIENT_B")
    warehouse_a = _create_warehouse(db_session, code="WH_A")
    warehouse_b = _create_warehouse(db_session, code="WH_B")
    _create_setting(db_session, client_id=client_a.id, warehouse_id=warehouse_a.id, usage_type="RETURN_GOOD")
    _create_setting(db_session, client_id=client_b.id, warehouse_id=warehouse_b.id, usage_type="STORAGE")
    _create_user(
        db_session,
        login_id="cw_nested_client_user",
        role_code="CLIENT_USER",
        permissions=["MASTER_VIEW"],
        client_id=client_a.id,
    )
    headers = _login(client, "cw_nested_client_user")

    own_response = client.get(f"/api/master/clients/{client_a.id}/warehouse-settings", headers=headers)
    other_response = client.get(f"/api/master/clients/{client_b.id}/warehouse-settings", headers=headers)

    assert own_response.status_code == 200
    assert len(own_response.json()["data"]) == 1
    assert own_response.json()["data"][0]["client_id"] == client_a.id
    assert other_response.status_code == 403
    assert other_response.json()["result_code"] == "CLIENT_SCOPE_DENIED"


def test_warehouse_options_show_linked_usage_types(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    warehouse_active = _create_warehouse(db_session, code="WH_ACTIVE")
    warehouse_available = _create_warehouse(db_session, code="WH_AVAILABLE")
    warehouse_inactive = _create_warehouse(db_session, code="WH_INACTIVE", active_yn=False)
    _create_setting(
        db_session,
        client_id=client_row.id,
        warehouse_id=warehouse_active.id,
        usage_type="RETURN_GOOD",
        is_default=True,
    )
    _create_user(db_session, login_id="cw_options", role_code="INTERNAL_ADMIN", permissions=_manage_permissions())
    headers = _login(client, "cw_options")

    response = client.get(f"/api/master/clients/{client_row.id}/warehouse-options", headers=headers)
    include_inactive_response = client.get(
        f"/api/master/clients/{client_row.id}/warehouse-options?include_inactive=true",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["result_code"] == "MASTER_CLIENT_WAREHOUSE_OPTIONS_FOUND"
    assert {item["warehouse_id"] for item in data["data"]} == {warehouse_active.id, warehouse_available.id}
    linked = next(item for item in data["data"] if item["warehouse_id"] == warehouse_active.id)
    available = next(item for item in data["data"] if item["warehouse_id"] == warehouse_available.id)
    assert linked["already_linked"] is True
    assert linked["linked_usage_types"] == ["RETURN_GOOD"]
    assert linked["default_usage_types"] == ["RETURN_GOOD"]
    assert available["already_linked"] is False
    assert include_inactive_response.status_code == 200
    assert warehouse_inactive.id in {item["warehouse_id"] for item in include_inactive_response.json()["data"]}


def test_nested_client_warehouse_create_update_default_disable_enable(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    warehouse_a = _create_warehouse(db_session, code="WH_A")
    warehouse_b = _create_warehouse(db_session, code="WH_B")
    old_default = _create_setting(
        db_session,
        client_id=client_row.id,
        warehouse_id=warehouse_a.id,
        usage_type="RETURN_GOOD",
        is_default=True,
    )
    _create_user(db_session, login_id="cw_nested_manage", role_code="INTERNAL_ADMIN", permissions=_manage_permissions())
    headers = _login(client, "cw_nested_manage")

    create_response = client.post(
        f"/api/master/clients/{client_row.id}/warehouse-settings",
        json={"warehouse_id": warehouse_b.id, "usage_type": "STORAGE", "is_default": False},
        headers=headers,
    )
    assert create_response.status_code == 200
    created = create_response.json()["data"]
    setting_id = created["setting_id"]
    assert created["client_id"] == client_row.id
    assert created["usage_type_label"] == "보관"
    assert created["allowed_actions"]["can_update"] is True
    assert created["allowed_actions"]["can_disable"] is True

    update_response = client.patch(
        f"/api/master/clients/{client_row.id}/warehouse-settings/{setting_id}",
        json={"usage_type": "RETURN_GOOD"},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["usage_type"] == "RETURN_GOOD"

    default_response = client.post(
        f"/api/master/clients/{client_row.id}/warehouse-settings/{setting_id}/set-default",
        headers=headers,
    )
    assert default_response.status_code == 200
    assert default_response.json()["data"]["is_default"] is True
    db_session.refresh(old_default)
    assert old_default.is_default is False

    default_disable_response = client.post(
        f"/api/master/clients/{client_row.id}/warehouse-settings/{setting_id}/disable",
        headers=headers,
    )
    assert default_disable_response.status_code == 400
    assert default_disable_response.json()["result_code"] == "MASTER_CLIENT_WAREHOUSE_DEFAULT_DISABLE_DENIED"

    other_setting = _create_setting(
        db_session,
        client_id=client_row.id,
        warehouse_id=warehouse_a.id,
        usage_type="STORAGE",
        is_default=False,
    )
    disable_response = client.post(
        f"/api/master/clients/{client_row.id}/warehouse-settings/{other_setting.id}/disable",
        headers=headers,
    )
    assert disable_response.status_code == 200
    assert disable_response.json()["data"]["active_yn"] is False

    inactive_default_response = client.post(
        f"/api/master/clients/{client_row.id}/warehouse-settings/{other_setting.id}/set-default",
        headers=headers,
    )
    assert inactive_default_response.status_code == 400
    assert inactive_default_response.json()["result_code"] == "MASTER_CLIENT_WAREHOUSE_INACTIVE"

    enable_response = client.post(
        f"/api/master/clients/{client_row.id}/warehouse-settings/{other_setting.id}/enable",
        headers=headers,
    )
    assert enable_response.status_code == 200
    assert enable_response.json()["data"]["active_yn"] is True
    assert enable_response.json()["data"]["is_default"] is False


def test_nested_client_warehouse_setting_id_must_match_client(client: TestClient, db_session: Session):
    client_a = _create_client(db_session, code="CLIENT_A")
    client_b = _create_client(db_session, code="CLIENT_B")
    warehouse = _create_warehouse(db_session)
    setting = _create_setting(db_session, client_id=client_a.id, warehouse_id=warehouse.id)
    _create_user(db_session, login_id="cw_nested_mismatch", role_code="INTERNAL_ADMIN", permissions=_manage_permissions())

    response = client.post(
        f"/api/master/clients/{client_b.id}/warehouse-settings/{setting.id}/set-default",
        headers=_login(client, "cw_nested_mismatch"),
    )

    assert response.status_code == 404
    assert response.json()["result_code"] == "MASTER_CLIENT_WAREHOUSE_NOT_FOUND"


def test_nested_client_warehouse_unknown_client_returns_404(client: TestClient, db_session: Session):
    _create_user(db_session, login_id="cw_nested_missing_client", role_code="INTERNAL_ADMIN", permissions=["MASTER_VIEW"])

    response = client.get(
        "/api/master/clients/999999/warehouse-settings",
        headers=_login(client, "cw_nested_missing_client"),
    )

    assert response.status_code == 404
    assert response.json()["result_code"] == "MASTER_CLIENT_NOT_FOUND"
