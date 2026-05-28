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
from app.models.master import Client, Warehouse


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


def _create_client(db: Session) -> Client:
    client = Client(client_code="CLIENT_A", client_name="Test Client", active_yn=True)
    db.add(client)
    db.commit()
    return client


def _create_warehouse(db: Session, code: str = "WH_A", name: str = "Test Warehouse") -> Warehouse:
    warehouse = Warehouse(warehouse_code=code, warehouse_name=name, warehouse_type="RETURN", active_yn=True)
    db.add(warehouse)
    db.commit()
    return warehouse


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


def _warehouse_payload(**overrides) -> dict:
    payload = {
        "warehouse_code": "WH_NEW",
        "warehouse_name": "New Warehouse",
        "warehouse_type": "RETURN",
        "address": "Local Test Address",
        "remarks": "test",
    }
    payload.update(overrides)
    return payload


def _assert_no_sensitive_values(data: dict) -> None:
    text = str(data).lower()
    for value in ("password", "secret", "token", "hash"):
        assert value not in text


def test_warehouse_manage_requires_auth(client: TestClient):
    response = client.post("/api/master/warehouses", json=_warehouse_payload())

    assert response.status_code == 401
    assert response.json()["result_code"] == "NOT_AUTHENTICATED"


@pytest.mark.parametrize("role_code", ["READ_ONLY", "CLIENT_ADMIN", "INTERNAL_WORKER"])
def test_warehouse_manage_blocks_roles_without_manage_permission(
    client: TestClient,
    db_session: Session,
    role_code: str,
):
    user_client_id = _create_client(db_session).id if role_code in {"READ_ONLY", "CLIENT_ADMIN"} else None
    _create_user(
        db_session,
        login_id=f"blocked_warehouse_{role_code.lower()}",
        role_code=role_code,
        permissions=["MASTER_VIEW"],
        client_id=user_client_id,
    )

    response = client.post(
        "/api/master/warehouses",
        json=_warehouse_payload(),
        headers=_login(client, f"blocked_warehouse_{role_code.lower()}"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "PERMISSION_DENIED"


def test_internal_admin_can_create_warehouse(client: TestClient, db_session: Session):
    _create_user(
        db_session,
        login_id="warehouse_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )

    response = client.post(
        "/api/master/warehouses",
        json=_warehouse_payload(),
        headers=_login(client, "warehouse_admin"),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["result_code"] == "MASTER_WAREHOUSE_CREATED"
    assert data["data"]["warehouse_code"] == "WH_NEW"
    assert data["data"]["warehouse_type"] == "RETURN"
    _assert_no_sensitive_values(data)


def test_warehouse_create_blocks_duplicate_warehouse_code(client: TestClient, db_session: Session):
    _create_warehouse(db_session, code="WH_DUP")
    _create_user(
        db_session,
        login_id="duplicate_warehouse_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )

    response = client.post(
        "/api/master/warehouses",
        json=_warehouse_payload(warehouse_code="WH_DUP", warehouse_name="Duplicate Warehouse"),
        headers=_login(client, "duplicate_warehouse_admin"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "MASTER_WAREHOUSE_CODE_DUPLICATED"


def test_warehouse_update_does_not_change_warehouse_code(client: TestClient, db_session: Session):
    warehouse = _create_warehouse(db_session, code="WH_KEEP")
    _create_user(
        db_session,
        login_id="warehouse_update_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )

    response = client.patch(
        f"/api/master/warehouses/{warehouse.id}",
        json={
            "warehouse_code": "WH_CHANGED",
            "warehouse_name": "Updated Warehouse",
            "warehouse_type": "INBOUND",
            "remarks": "updated",
        },
        headers=_login(client, "warehouse_update_admin"),
    )
    db_session.refresh(warehouse)

    assert response.status_code == 200
    assert response.json()["result_code"] == "MASTER_WAREHOUSE_UPDATED"
    assert response.json()["data"]["warehouse_name"] == "Updated Warehouse"
    assert response.json()["data"]["warehouse_type"] == "INBOUND"
    assert warehouse.warehouse_code == "WH_KEEP"


def test_warehouse_disable_enable(client: TestClient, db_session: Session):
    warehouse = _create_warehouse(db_session)
    _create_user(
        db_session,
        login_id="warehouse_active_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )
    headers = _login(client, "warehouse_active_admin")

    disable_response = client.post(f"/api/master/warehouses/{warehouse.id}/disable", headers=headers)
    enable_response = client.post(f"/api/master/warehouses/{warehouse.id}/enable", headers=headers)

    assert disable_response.status_code == 200
    assert disable_response.json()["result_code"] == "MASTER_WAREHOUSE_DISABLED"
    assert disable_response.json()["data"]["active_yn"] is False
    assert enable_response.status_code == 200
    assert enable_response.json()["result_code"] == "MASTER_WAREHOUSE_ENABLED"
    assert enable_response.json()["data"]["active_yn"] is True
