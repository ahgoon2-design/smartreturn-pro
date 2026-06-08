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
from app.models.channels import ChannelAccount, ChannelRawEvent, ChannelSyncJob
from app.models.master import Client, ClientUnit, Warehouse


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
        ClientUnit.__table__,
        Role.__table__,
        Permission.__table__,
        User.__table__,
        UserRole.__table__,
        RolePermission.__table__,
        ChannelAccount.__table__,
        ChannelSyncJob.__table__,
        ChannelRawEvent.__table__,
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


def _create_client(db: Session, code: str = "CLIENT_A") -> Client:
    row = Client(client_code=code, client_name=f"{code} Name", active_yn=True)
    db.add(row)
    db.commit()
    return row


def _create_unit(db: Session, client_id: int, code: str = "UNIT_A") -> ClientUnit:
    row = ClientUnit(client_id=client_id, unit_code=code, unit_name=f"{code} Name", active_yn=True)
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


def _admin_headers(client: TestClient, db: Session, login_id: str = "channel_admin") -> dict[str, str]:
    _create_user(
        db,
        login_id=login_id,
        role_code="INTERNAL_ADMIN",
        permissions=["RETURN_VIEW", "RETURN_MANAGE"],
    )
    return _login(client, login_id)


def _account_payload(client_id: int, **overrides) -> dict:
    payload = {
        "client_id": client_id,
        "channel_type": "NAVER_SMARTSTORE",
        "account_name": "네이버 기본 계정",
        "store_name": "테스트 스토어",
        "external_account_id": "store-dry-run",
        "credential_ref": "channel/naver/test-store",
        "sync_enabled": True,
    }
    payload.update(overrides)
    return payload


def _create_account(client: TestClient, headers: dict[str, str], client_id: int, **overrides) -> int:
    response = client.post("/api/channels/accounts", headers=headers, json=_account_payload(client_id, **overrides))
    assert response.status_code == 200
    return response.json()["data"]["id"]


def _assert_no_secret_fields(data) -> None:
    text = str(data).lower()
    assert "secret" not in text
    assert "password" not in text
    assert "token" not in text
    assert "password_hash" not in text
    assert "credential_ref':" not in text


def test_channel_account_create_list_update_disable(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    unit = _create_unit(db_session, client_row.id)
    headers = _admin_headers(client, db_session)

    account_id = _create_account(client, headers, client_row.id, client_unit_id=unit.id)

    list_response = client.get("/api/channels/accounts", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["data"]["items"][0]["id"] == account_id
    assert list_response.json()["data"]["items"][0]["credential_ref_masked"] == "chan***tore"

    update_response = client.patch(
        f"/api/channels/accounts/{account_id}",
        headers=headers,
        json={"store_name": "수정 스토어", "sync_enabled": False},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["store_name"] == "수정 스토어"
    assert update_response.json()["data"]["sync_enabled"] is False

    disable_response = client.post(f"/api/channels/accounts/{account_id}/disable", headers=headers)
    assert disable_response.status_code == 200
    assert disable_response.json()["data"]["status"] == "INACTIVE"
    assert disable_response.json()["data"]["sync_enabled"] is False


def test_channel_accounts_respect_client_scope(client: TestClient, db_session: Session):
    client_a = _create_client(db_session, "CLIENT_A")
    client_b = _create_client(db_session, "CLIENT_B")
    admin_headers = _admin_headers(client, db_session)
    account_a_id = _create_account(client, admin_headers, client_a.id, external_account_id="store-a")
    account_b_id = _create_account(client, admin_headers, client_b.id, external_account_id="store-b")

    _create_user(
        db_session,
        login_id="client_user",
        role_code="CLIENT_ADMIN",
        permissions=["RETURN_VIEW"],
        client_id=client_a.id,
    )
    client_headers = _login(client, "client_user")

    list_response = client.get("/api/channels/accounts", headers=client_headers)
    assert list_response.status_code == 200
    ids = {item["id"] for item in list_response.json()["data"]["items"]}
    assert ids == {account_a_id}

    blocked_response = client.get(f"/api/channels/accounts/{account_b_id}", headers=client_headers)
    assert blocked_response.status_code == 403


def test_channel_connection_dry_run_does_not_expose_secrets(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    headers = _admin_headers(client, db_session)
    account_id = _create_account(client, headers, client_row.id)

    response = client.post(f"/api/channels/accounts/{account_id}/test-connection", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["dry_run"] is True
    assert data["success"] is True
    assert data["provider_name"] == "NAVER_SMARTSTORE_DRY_RUN"
    _assert_no_secret_fields(data)


def test_channel_dry_run_creates_job_and_raw_event_without_raw_json_in_list(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    headers = _admin_headers(client, db_session)
    account_id = _create_account(client, headers, client_row.id)

    response = client.post(f"/api/channels/accounts/{account_id}/sync-jobs/dry-run", headers=headers, json={})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["dry_run"] is True
    assert data["collected_event_count"] == 1
    assert data["inserted_event_count"] == 1
    assert data["updated_event_count"] == 0
    assert data["job"]["status"] == "SUCCESS"

    events_response = client.get("/api/channels/raw-events", headers=headers)
    assert events_response.status_code == 200
    event_item = events_response.json()["data"]["items"][0]
    assert event_item["channel_type"] == "NAVER_SMARTSTORE"
    assert event_item["external_tracking_no_hash"]
    assert "raw_json" not in event_item


def test_channel_raw_event_dry_run_upserts_duplicate(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    headers = _admin_headers(client, db_session)
    account_id = _create_account(client, headers, client_row.id)

    first_response = client.post(f"/api/channels/accounts/{account_id}/sync-jobs/dry-run", headers=headers, json={})
    second_response = client.post(f"/api/channels/accounts/{account_id}/sync-jobs/dry-run", headers=headers, json={})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["data"]["inserted_event_count"] == 1
    assert second_response.json()["data"]["inserted_event_count"] == 0
    assert second_response.json()["data"]["updated_event_count"] == 1
    assert db_session.query(ChannelRawEvent).count() == 1


def test_channel_account_rejects_literal_secret_like_credential_ref(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    headers = _admin_headers(client, db_session)

    response = client.post(
        "/api/channels/accounts",
        headers=headers,
        json=_account_payload(client_row.id, credential_ref="secret-real-value"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "CHANNEL_CREDENTIAL_REF_UNSAFE"
