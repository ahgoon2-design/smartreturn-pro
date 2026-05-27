from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.auth import User
from app.models.master import Client, Warehouse


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (Client.__table__, Warehouse.__table__, User.__table__):
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


def _create_user(db: Session) -> User:
    user = User(
        login_id="tester",
        user_name="테스터",
        password_hash=hash_password("DummyPass123!"),
        active_yn=True,
        must_change_password=True,
    )
    db.add(user)
    db.commit()
    return user


def _payload(**overrides) -> dict[str, str]:
    data = {
        "current_password": "DummyPass123!",
        "new_password": "NewDummyPass123!",
        "new_password_confirm": "NewDummyPass123!",
    }
    data.update(overrides)
    return data


def _assert_response_has_no_password_material(data: dict) -> None:
    response_text = str(data)
    assert "DummyPass123!" not in response_text
    assert "NewDummyPass123!" not in response_text
    assert "password_hash" not in response_text
    assert "current_password" not in response_text
    assert "new_password" not in response_text


def test_change_password_api_success(client: TestClient, db_session: Session):
    user = _create_user(db_session)

    response = client.post(
        "/api/auth/password/change",
        json=_payload(),
        headers={"X-Test-User-Id": str(user.id)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["result_code"] == "PASSWORD_CHANGED"
    assert data["must_change_password"] is False
    _assert_response_has_no_password_material(data)


def test_change_password_api_requires_test_user_header(client: TestClient):
    response = client.post("/api/auth/password/change", json=_payload())

    assert response.status_code == 401
    assert response.json()["detail"]["result_code"] == "NOT_AUTHENTICATED"


def test_change_password_api_rejects_wrong_current_password(client: TestClient, db_session: Session):
    user = _create_user(db_session)

    response = client.post(
        "/api/auth/password/change",
        json=_payload(current_password="WrongPass123!"),
        headers={"X-Test-User-Id": str(user.id)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["result_code"] == "INVALID_CURRENT_PASSWORD"
    _assert_response_has_no_password_material(data)
