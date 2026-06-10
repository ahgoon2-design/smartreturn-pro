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
from app.models.master import Client, CommonCode, CommonCodeGroup


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
        CommonCodeGroup.__table__,
        CommonCode.__table__,
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


def _create_group(
    db: Session,
    *,
    group_code: str = "RETURN_STATUS",
    group_name: str = "Return Status",
    active_yn: bool = True,
) -> CommonCodeGroup:
    group = CommonCodeGroup(group_code=group_code, group_name=group_name, active_yn=active_yn)
    db.add(group)
    db.commit()
    return group


def _create_client(db: Session) -> Client:
    client = Client(client_code="CLIENT_A", client_name="Test Client", active_yn=True)
    db.add(client)
    db.commit()
    return client


def _create_code(
    db: Session,
    group_id: int,
    *,
    code_value: str = "CREATED",
    code_name: str = "Created",
    sort_order: int = 1,
    system_yn: bool = False,
    locked_yn: bool = False,
    active_yn: bool = True,
) -> CommonCode:
    code = CommonCode(
        group_id=group_id,
        code_value=code_value,
        code_name=code_name,
        sort_order=sort_order,
        system_yn=system_yn,
        locked_yn=locked_yn,
        active_yn=active_yn,
    )
    db.add(code)
    db.commit()
    return code


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
    return ["MASTER_MANAGE", "COMMON_CODE_MANAGE"]


def _group_payload(**overrides) -> dict:
    payload = {
        "group_code": "RETURN_STATUS",
        "group_name": "Return Status",
        "description": "test",
    }
    payload.update(overrides)
    return payload


def _code_payload(group_id: int, **overrides) -> dict:
    payload = {
        "group_id": group_id,
        "code_value": "CREATED",
        "code_name": "Created",
        "sort_order": 1,
        "description": "test",
    }
    payload.update(overrides)
    return payload


def _assert_no_sensitive_values(data: dict) -> None:
    text = str(data).lower()
    for value in ("password", "secret", "token", "hash"):
        assert value not in text


def test_common_code_manage_requires_auth(client: TestClient):
    response = client.post("/api/master/common-code-groups", json=_group_payload())

    assert response.status_code == 401
    assert response.json()["result_code"] == "NOT_AUTHENTICATED"


@pytest.mark.parametrize("role_code", ["READ_ONLY", "CLIENT_ADMIN", "INTERNAL_WORKER"])
def test_common_code_manage_blocks_roles_without_manage_permission(
    client: TestClient,
    db_session: Session,
    role_code: str,
    ):
    client_id = None
    if role_code in {"READ_ONLY", "CLIENT_ADMIN"}:
        client_id = _create_client(db_session).id
    _create_user(
        db_session,
        login_id=f"blocked_common_{role_code.lower()}",
        role_code=role_code,
        permissions=["MASTER_VIEW"],
        client_id=client_id,
    )

    response = client.post(
        "/api/master/common-code-groups",
        json=_group_payload(),
        headers=_login(client, f"blocked_common_{role_code.lower()}"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "PERMISSION_DENIED"


def test_internal_admin_can_create_common_code_group(client: TestClient, db_session: Session):
    _create_user(
        db_session,
        login_id="common_group_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )

    response = client.post(
        "/api/master/common-code-groups",
        json=_group_payload(),
        headers=_login(client, "common_group_admin"),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["result_code"] == "MASTER_COMMON_CODE_GROUP_CREATED"
    assert data["data"]["group_code"] == "RETURN_STATUS"
    _assert_no_sensitive_values(data)


def test_common_code_group_create_blocks_duplicate_group_code(client: TestClient, db_session: Session):
    _create_group(db_session, group_code="RETURN_STATUS")
    _create_user(
        db_session,
        login_id="duplicate_group_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )

    response = client.post(
        "/api/master/common-code-groups",
        json=_group_payload(group_name="Duplicate"),
        headers=_login(client, "duplicate_group_admin"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "MASTER_COMMON_CODE_GROUP_DUPLICATED"


def test_common_code_group_update_does_not_change_group_code(client: TestClient, db_session: Session):
    group = _create_group(db_session, group_code="RETURN_STATUS")
    _create_user(
        db_session,
        login_id="group_update_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )

    response = client.patch(
        f"/api/master/common-code-groups/{group.id}",
        json={"group_code": "CHANGED", "group_name": "Updated Status", "description": "updated"},
        headers=_login(client, "group_update_admin"),
    )
    db_session.refresh(group)

    assert response.status_code == 200
    assert response.json()["result_code"] == "MASTER_COMMON_CODE_GROUP_UPDATED"
    assert response.json()["data"]["group_name"] == "Updated Status"
    assert group.group_code == "RETURN_STATUS"


def test_common_code_group_disable_enable(client: TestClient, db_session: Session):
    group = _create_group(db_session)
    _create_user(
        db_session,
        login_id="group_active_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )
    headers = _login(client, "group_active_admin")

    disable_response = client.post(f"/api/master/common-code-groups/{group.id}/disable", headers=headers)
    enable_response = client.post(f"/api/master/common-code-groups/{group.id}/enable", headers=headers)

    assert disable_response.status_code == 200
    assert disable_response.json()["result_code"] == "MASTER_COMMON_CODE_GROUP_DISABLED"
    assert disable_response.json()["data"]["active_yn"] is False
    assert enable_response.status_code == 200
    assert enable_response.json()["result_code"] == "MASTER_COMMON_CODE_GROUP_ENABLED"
    assert enable_response.json()["data"]["active_yn"] is True


def test_common_code_create_success(client: TestClient, db_session: Session):
    group = _create_group(db_session)
    _create_user(
        db_session,
        login_id="code_create_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )

    response = client.post(
        "/api/master/common-codes",
        json=_code_payload(group.id),
        headers=_login(client, "code_create_admin"),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["result_code"] == "MASTER_COMMON_CODE_CREATED"
    assert data["data"]["code_value"] == "CREATED"
    _assert_no_sensitive_values(data)


def test_common_code_create_blocks_duplicate_group_value(client: TestClient, db_session: Session):
    group = _create_group(db_session)
    _create_code(db_session, group.id, code_value="CREATED")
    _create_user(
        db_session,
        login_id="duplicate_code_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )

    response = client.post(
        "/api/master/common-codes",
        json=_code_payload(group.id, code_name="Duplicate"),
        headers=_login(client, "duplicate_code_admin"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "MASTER_COMMON_CODE_DUPLICATED"


def test_common_code_create_blocks_inactive_group(client: TestClient, db_session: Session):
    group = _create_group(db_session, active_yn=False)
    _create_user(
        db_session,
        login_id="inactive_group_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )

    response = client.post(
        "/api/master/common-codes",
        json=_code_payload(group.id),
        headers=_login(client, "inactive_group_admin"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "MASTER_COMMON_CODE_GROUP_INACTIVE"


def test_common_code_update_does_not_change_code_value(client: TestClient, db_session: Session):
    group = _create_group(db_session)
    code = _create_code(db_session, group.id, code_value="CREATED")
    _create_user(
        db_session,
        login_id="code_update_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )

    response = client.patch(
        f"/api/master/common-codes/{code.id}",
        json={"code_value": "CHANGED", "code_name": "Updated", "sort_order": 10, "description": "updated"},
        headers=_login(client, "code_update_admin"),
    )
    db_session.refresh(code)

    assert response.status_code == 200
    assert response.json()["result_code"] == "MASTER_COMMON_CODE_UPDATED"
    assert response.json()["data"]["code_name"] == "Updated"
    assert response.json()["data"]["sort_order"] == 10
    assert code.code_value == "CREATED"


def test_common_code_update_blocks_locked_code(client: TestClient, db_session: Session):
    group = _create_group(db_session)
    code = _create_code(db_session, group.id, locked_yn=True)
    _create_user(
        db_session,
        login_id="locked_update_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )

    response = client.patch(
        f"/api/master/common-codes/{code.id}",
        json={"code_name": "Updated"},
        headers=_login(client, "locked_update_admin"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "MASTER_COMMON_CODE_LOCKED"


@pytest.mark.parametrize("system_yn, locked_yn", [(True, False), (False, True)])
def test_common_code_disable_blocks_system_or_locked_code(
    client: TestClient,
    db_session: Session,
    system_yn: bool,
    locked_yn: bool,
):
    group = _create_group(db_session)
    code = _create_code(db_session, group.id, system_yn=system_yn, locked_yn=locked_yn)
    _create_user(
        db_session,
        login_id=f"locked_disable_admin_{system_yn}_{locked_yn}",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )

    response = client.post(
        f"/api/master/common-codes/{code.id}/disable",
        headers=_login(client, f"locked_disable_admin_{system_yn}_{locked_yn}"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "MASTER_COMMON_CODE_LOCKED"


def test_common_code_disable_enable(client: TestClient, db_session: Session):
    group = _create_group(db_session)
    code = _create_code(db_session, group.id)
    _create_user(
        db_session,
        login_id="code_active_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )
    headers = _login(client, "code_active_admin")

    disable_response = client.post(f"/api/master/common-codes/{code.id}/disable", headers=headers)
    enable_response = client.post(f"/api/master/common-codes/{code.id}/enable", headers=headers)

    assert disable_response.status_code == 200
    assert disable_response.json()["result_code"] == "MASTER_COMMON_CODE_DISABLED"
    assert disable_response.json()["data"]["active_yn"] is False
    assert enable_response.status_code == 200
    assert enable_response.json()["result_code"] == "MASTER_COMMON_CODE_ENABLED"
    assert enable_response.json()["data"]["active_yn"] is True
