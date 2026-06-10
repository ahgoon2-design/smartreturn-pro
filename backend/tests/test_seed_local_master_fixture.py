from __future__ import annotations

import json
import shutil
import sys
from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.master import Client


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = BACKEND_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from _local_config import LocalConfigError, load_local_secret_config  # noqa: E402
from reset_local_admin_password import ensure_database_url_is_local  # noqa: E402
from seed_local_master_fixture import (  # noqa: E402
    LOCAL_FIXTURE_CLIENT_CODE,
    LOCAL_FIXTURE_CLIENT_NAME,
    SeedLocalMasterFixtureError,
    seed_from_local_secret,
    seed_local_master_fixture,
)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Client.__table__.create(bind=engine)

    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def _test_dir() -> Path:
    path = BACKEND_ROOT / "tmp" / "test_seed_local_master_fixture" / uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    return path


def _write_config(data: dict) -> Path:
    path = _test_dir() / "local.secret.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _valid_config() -> dict:
    return {
        "environment": "local",
        "api": {"base_url": "http://127.0.0.1:8000"},
        "database": {"url": ""},
        "auth": {
            "admin_login_id": "local_super_admin",
            "current_password": "",
            "new_password": "NewDummyPass123!",
        },
    }


def test_seed_from_local_secret_requires_confirm_option() -> None:
    with pytest.raises(SeedLocalMasterFixtureError, match="--confirm-local-fixture"):
        seed_from_local_secret(confirm_local_fixture=False)


def test_load_config_rejects_non_local_environment() -> None:
    data = _valid_config()
    data["environment"] = "production"
    config_path = _write_config(data)

    with pytest.raises(LocalConfigError, match="environment=local"):
        load_local_secret_config(config_path, require_current_password=False)


def test_non_local_database_url_is_blocked_without_leaking_url() -> None:
    database_url = "postgresql+psycopg://user:secret@db.example.com:5432/smartreturn_pro"

    with pytest.raises(Exception) as exc_info:
        ensure_database_url_is_local(database_url)

    error_text = str(exc_info.value)
    assert "db.example.com" not in error_text
    assert "secret" not in error_text


def test_seed_creates_local_test_client(db_session: Session) -> None:
    result = seed_local_master_fixture(db_session)

    client = db_session.query(Client).filter(Client.client_code == LOCAL_FIXTURE_CLIENT_CODE).one()
    assert result.result_code == "LOCAL_MASTER_FIXTURE_CREATED"
    assert result.action == "created"
    assert result.client_id == client.id
    assert client.client_name == LOCAL_FIXTURE_CLIENT_NAME
    assert client.active_yn is True


def test_seed_reuses_existing_active_client(db_session: Session) -> None:
    client = Client(
        client_code=LOCAL_FIXTURE_CLIENT_CODE,
        client_name=LOCAL_FIXTURE_CLIENT_NAME,
        active_yn=True,
    )
    db_session.add(client)
    db_session.commit()

    result = seed_local_master_fixture(db_session)

    assert result.result_code == "LOCAL_MASTER_FIXTURE_REUSED"
    assert result.action == "reused"
    assert db_session.query(Client).filter(Client.client_code == LOCAL_FIXTURE_CLIENT_CODE).count() == 1


def test_seed_rejects_existing_inactive_client_without_reactivate(db_session: Session) -> None:
    client = Client(
        client_code=LOCAL_FIXTURE_CLIENT_CODE,
        client_name=LOCAL_FIXTURE_CLIENT_NAME,
        active_yn=False,
    )
    db_session.add(client)
    db_session.commit()

    with pytest.raises(SeedLocalMasterFixtureError, match="--reactivate-existing"):
        seed_local_master_fixture(db_session)

    db_session.refresh(client)
    assert client.active_yn is False


def test_seed_reactivates_existing_inactive_client_when_requested(db_session: Session) -> None:
    client = Client(
        client_code=LOCAL_FIXTURE_CLIENT_CODE,
        client_name=LOCAL_FIXTURE_CLIENT_NAME,
        active_yn=False,
    )
    db_session.add(client)
    db_session.commit()

    result = seed_local_master_fixture(db_session, reactivate_existing=True)

    db_session.refresh(client)
    assert result.result_code == "LOCAL_MASTER_FIXTURE_REACTIVATED"
    assert result.action == "reactivated"
    assert client.active_yn is True


def test_fixture_uses_only_local_test_data(db_session: Session) -> None:
    seed_local_master_fixture(db_session)

    client = db_session.query(Client).filter(Client.client_code == LOCAL_FIXTURE_CLIENT_CODE).one()
    assert client.client_code == "LOCAL_TEST_CLIENT"
    assert client.client_name == "로컬검증고객사"
    assert not client.business_no
    assert not client.contact_name
    assert not client.contact_phone
    assert not client.contact_email


def test_error_message_does_not_include_secret_words(db_session: Session) -> None:
    client = Client(
        client_code=LOCAL_FIXTURE_CLIENT_CODE,
        client_name=LOCAL_FIXTURE_CLIENT_NAME,
        active_yn=False,
    )
    db_session.add(client)
    db_session.commit()

    with pytest.raises(SeedLocalMasterFixtureError) as exc_info:
        seed_local_master_fixture(db_session)

    error_text = str(exc_info.value).lower()
    assert "password" not in error_text
    assert "secret" not in error_text
    assert "postgresql" not in error_text


def teardown_module() -> None:
    shutil.rmtree(BACKEND_ROOT / "tmp" / "test_seed_local_master_fixture", ignore_errors=True)
