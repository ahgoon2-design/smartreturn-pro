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

from app.core.security import hash_password, verify_password
from app.models.auth import Role, User, UserRole
from app.models.master import Client, Warehouse


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = BACKEND_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from _local_config import LocalConfigError, load_local_secret_config  # noqa: E402
from reset_local_admin_password import (  # noqa: E402
    ResetLocalAdminPasswordError,
    ensure_database_url_is_local,
    reset_from_local_secret,
    reset_local_admin_password,
)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    for table in (
        Client.__table__,
        Warehouse.__table__,
        Role.__table__,
        User.__table__,
        UserRole.__table__,
    ):
        table.create(bind=engine)

    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def _add_role(db: Session, role_code: str = "SUPER_ADMIN") -> Role:
    role = Role(
        role_code=role_code,
        role_name="테스트 역할",
        role_type="INTERNAL",
        active_yn=True,
    )
    db.add(role)
    db.commit()
    return role


def _add_user(
    db: Session,
    *,
    login_id: str = "local_super_admin",
    password: str = "OldDummyPass123!",
    active_yn: bool = True,
    role: Role | None = None,
) -> User:
    user = User(
        login_id=login_id,
        user_name="테스트 관리자",
        password_hash=hash_password(password),
        must_change_password=True,
        active_yn=active_yn,
    )
    db.add(user)
    db.flush()
    if role is not None:
        db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    return user


def _test_dir() -> Path:
    path = BACKEND_ROOT / "tmp" / "test_reset_local_admin_password" / uuid4().hex
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


def test_reset_changes_password_hash_and_clears_must_change_password(
    db_session: Session,
) -> None:
    role = _add_role(db_session)
    user = _add_user(db_session, role=role)
    old_hash = user.password_hash

    result = reset_local_admin_password(
        db_session,
        login_id="local_super_admin",
        new_password="NewDummyPass123!",
    )

    db_session.refresh(user)
    assert result.result_code == "PASSWORD_RESET"
    assert result.must_change_password is False
    assert user.password_hash != old_hash
    assert verify_password("NewDummyPass123!", user.password_hash) is True
    assert user.must_change_password is False


def test_reset_can_keep_must_change_password_true(db_session: Session) -> None:
    role = _add_role(db_session)
    user = _add_user(db_session, role=role)

    result = reset_local_admin_password(
        db_session,
        login_id="local_super_admin",
        new_password="NewDummyPass123!",
        must_change_password=True,
    )

    db_session.refresh(user)
    assert result.must_change_password is True
    assert user.must_change_password is True


def test_load_config_for_reset_allows_empty_current_password() -> None:
    config_path = _write_config(_valid_config())

    config = load_local_secret_config(config_path, require_current_password=False)

    assert config.auth.admin_login_id == "local_super_admin"
    assert config.auth.current_password == ""


def test_load_config_for_reset_rejects_non_local_environment() -> None:
    data = _valid_config()
    data["environment"] = "production"
    config_path = _write_config(data)

    with pytest.raises(LocalConfigError, match="environment=local"):
        load_local_secret_config(config_path, require_current_password=False)


def test_load_config_for_reset_rejects_empty_new_password() -> None:
    data = _valid_config()
    data["auth"]["new_password"] = ""
    config_path = _write_config(data)

    with pytest.raises(LocalConfigError, match="auth.new_password"):
        load_local_secret_config(config_path, require_current_password=False)


def test_reset_from_local_secret_requires_confirm_option() -> None:
    with pytest.raises(ResetLocalAdminPasswordError, match="--confirm-local-reset"):
        reset_from_local_secret(confirm_local_reset=False)


def test_reset_rejects_user_without_super_admin_role(db_session: Session) -> None:
    _add_user(db_session)

    with pytest.raises(ResetLocalAdminPasswordError, match="SUPER_ADMIN"):
        reset_local_admin_password(
            db_session,
            login_id="local_super_admin",
            new_password="NewDummyPass123!",
        )


def test_reset_rejects_inactive_user(db_session: Session) -> None:
    role = _add_role(db_session)
    _add_user(db_session, role=role, active_yn=False)

    with pytest.raises(ResetLocalAdminPasswordError, match="비활성"):
        reset_local_admin_password(
            db_session,
            login_id="local_super_admin",
            new_password="NewDummyPass123!",
        )


def test_non_local_database_url_is_blocked() -> None:
    with pytest.raises(ResetLocalAdminPasswordError, match="로컬 DB host"):
        ensure_database_url_is_local(
            "postgresql+psycopg://user:password@db.example.com:5432/smartreturn_pro"
        )


def test_localhost_database_url_is_allowed() -> None:
    ensure_database_url_is_local(
        "postgresql+psycopg://user:password@localhost:5432/smartreturn_pro"
    )


def test_error_message_does_not_include_new_password_or_hash(
    db_session: Session,
) -> None:
    role = _add_role(db_session)
    _add_user(db_session, role=role)
    secret_password = "short"

    with pytest.raises(ResetLocalAdminPasswordError) as exc_info:
        reset_local_admin_password(
            db_session,
            login_id="local_super_admin",
            new_password=secret_password,
        )

    error_text = str(exc_info.value)
    assert secret_password not in error_text
    assert "password_hash" not in error_text


def teardown_module() -> None:
    shutil.rmtree(BACKEND_ROOT / "tmp" / "test_reset_local_admin_password", ignore_errors=True)
