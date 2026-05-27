from collections.abc import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.error_handlers import auth_error_to_response, register_error_handlers
from app.core.exceptions import InvalidTokenError, PermissionDeniedError
from app.core.jwt import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.auth import Permission, Role, RolePermission, User, UserRole
from app.models.master import Client, Warehouse


def _assert_api_error_shape(data: dict, result_code: str) -> None:
    assert data["success"] is False
    assert data["result_code"] == result_code
    assert data["message"]
    assert data["data"] is None
    assert data["warnings"] == []
    assert data["errors"] == []
    response_text = str(data)
    assert "password_hash" not in response_text
    assert "DummyPass123!" not in response_text
    assert "secret" not in response_text.lower()


def test_auth_error_to_response_uses_api_result_shape():
    response = auth_error_to_response(PermissionDeniedError("권한이 없습니다."))

    assert response.status_code == 403


def test_registered_auth_error_handler_returns_api_result():
    temp_app = FastAPI()
    register_error_handlers(temp_app)

    @temp_app.get("/blocked")
    def blocked():
        raise PermissionDeniedError("권한이 없습니다.")

    response = TestClient(temp_app).get("/blocked")

    assert response.status_code == 403
    _assert_api_error_shape(response.json(), "PERMISSION_DENIED")


def test_context_without_authorization_header_returns_api_result():
    response = TestClient(app).get("/api/auth/context")

    assert response.status_code == 401
    _assert_api_error_shape(response.json(), "NOT_AUTHENTICATED")


def test_context_with_invalid_token_returns_api_result():
    raw_token = "bad-token"
    response = TestClient(app).get("/api/auth/context", headers={"Authorization": f"Bearer {raw_token}"})

    assert response.status_code == 401
    _assert_api_error_shape(response.json(), "INVALID_TOKEN")
    assert raw_token not in str(response.json())


def test_expired_token_returns_api_result():
    token = create_access_token("1", expires_delta_minutes=-1)
    response = TestClient(app).get("/api/auth/context", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    _assert_api_error_shape(response.json(), "TOKEN_EXPIRED")
    assert token not in str(response.json())


def test_password_change_without_token_returns_api_result():
    response = TestClient(app).post(
        "/api/auth/password/change",
        json={
            "current_password": "DummyPass123!",
            "new_password": "NewDummyPass123!",
            "new_password_confirm": "NewDummyPass123!",
        },
    )

    assert response.status_code == 401
    _assert_api_error_shape(response.json(), "NOT_AUTHENTICATED")


def test_token_for_missing_user_returns_api_result():
    token = create_access_token("999")
    response = TestClient(app).get("/api/auth/context", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    _assert_api_error_shape(response.json(), "NOT_AUTHENTICATED")


def test_login_failure_returns_api_result_shape():
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

    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = TestClient(app).post(
            "/api/auth/login",
            json={"login_id": "missing", "password": "DummyPass123!"},
        )
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()

    assert response.status_code == 401
    _assert_api_error_shape(response.json(), "INVALID_LOGIN")


def test_invalid_token_error_message_has_no_sensitive_value():
    response = auth_error_to_response(InvalidTokenError("유효하지 않은 인증 토큰입니다."))
    body = response.body.decode("utf-8")

    assert "password_hash" not in body
    assert "DummyPass123!" not in body
