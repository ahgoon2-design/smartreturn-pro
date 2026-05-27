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


def _create_user(
    db: Session,
    *,
    login_id: str = "tester",
    password: str = "DummyPass123!",
    active_yn: bool = True,
    must_change_password: bool = True,
) -> User:
    role = Role(
        role_code="SUPER_ADMIN",
        role_name="최고 관리자",
        role_type="INTERNAL",
        active_yn=True,
    )
    permission = Permission(
        permission_code="SYSTEM_ADMIN",
        permission_name="시스템 관리",
        description="테스트용 권한",
        active_yn=True,
    )
    user = User(
        login_id=login_id,
        user_name="테스트",
        password_hash=hash_password(password),
        active_yn=active_yn,
        must_change_password=must_change_password,
    )
    db.add_all([role, permission, user])
    db.flush()
    db.add_all(
        [
            UserRole(user_id=user.id, role_id=role.id),
            RolePermission(role_id=role.id, permission_id=permission.id),
        ]
    )
    db.commit()
    return user


def _assert_no_password_material(data: dict) -> None:
    response_text = str(data)
    assert "DummyPass123!" not in response_text
    assert "password_hash" not in response_text
    assert "password" not in data


def test_login_success_returns_access_token(client: TestClient, db_session: Session):
    _create_user(db_session)

    response = client.post("/api/auth/login", json={"login_id": "tester", "password": "DummyPass123!"})

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["must_change_password"] is True
    assert data["user"]["roles"] == ["SUPER_ADMIN"]
    _assert_no_password_material(data)


def test_login_rejects_wrong_password(client: TestClient, db_session: Session):
    _create_user(db_session)

    response = client.post("/api/auth/login", json={"login_id": "tester", "password": "WrongPass123!"})

    assert response.status_code == 401
    assert response.json()["detail"]["result_code"] == "NOT_AUTHENTICATED"


def test_login_rejects_missing_user(client: TestClient):
    response = client.post("/api/auth/login", json={"login_id": "missing", "password": "DummyPass123!"})

    assert response.status_code == 401


def test_login_rejects_inactive_user(client: TestClient, db_session: Session):
    _create_user(db_session, active_yn=False)

    response = client.post("/api/auth/login", json={"login_id": "tester", "password": "DummyPass123!"})

    assert response.status_code == 401


def test_auth_context_with_issued_token(client: TestClient, db_session: Session):
    _create_user(db_session, must_change_password=False)
    login_response = client.post("/api/auth/login", json={"login_id": "tester", "password": "DummyPass123!"})
    token = login_response.json()["access_token"]

    response = client.get("/api/auth/context", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["login_id"] == "tester"
    assert data["roles"] == ["SUPER_ADMIN"]
    assert data["permissions"] == ["SYSTEM_ADMIN"]
    assert data["must_change_password"] is False


def test_auth_context_rejects_bad_token(client: TestClient):
    response = client.get("/api/auth/context", headers={"Authorization": "Bearer bad-token"})

    assert response.status_code == 401
