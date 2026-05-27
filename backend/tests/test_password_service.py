from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import hash_password, verify_password
from app.models.auth import User
from app.models.master import Client, Warehouse
from app.schemas.password import ChangePasswordRequest
from app.services.password_service import change_own_password


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    for table in (Client.__table__, Warehouse.__table__, User.__table__):
        table.create(bind=engine)

    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def _create_user(
    db: Session,
    *,
    password: str = "DummyPass123!",
    active_yn: bool = True,
    must_change_password: bool = True,
) -> User:
    user = User(
        login_id="tester",
        user_name="테스터",
        password_hash=hash_password(password),
        active_yn=active_yn,
        must_change_password=must_change_password,
    )
    db.add(user)
    db.commit()
    return user


def _request(
    *,
    current_password: str = "DummyPass123!",
    new_password: str = "NewDummyPass123!",
    new_password_confirm: str = "NewDummyPass123!",
) -> ChangePasswordRequest:
    return ChangePasswordRequest(
        current_password=current_password,
        new_password=new_password,
        new_password_confirm=new_password_confirm,
    )


def _assert_no_password_material(response_text: str) -> None:
    assert "DummyPass123!" not in response_text
    assert "NewDummyPass123!" not in response_text
    assert "password_hash" not in response_text
    assert "current_password" not in response_text
    assert "new_password" not in response_text


def test_change_own_password_updates_hash_and_clears_flag(db_session: Session):
    user = _create_user(db_session)
    old_hash = user.password_hash

    response = change_own_password(db_session, user.id, _request())

    db_session.refresh(user)
    assert response.success is True
    assert response.result_code == "PASSWORD_CHANGED"
    assert response.must_change_password is False
    assert user.must_change_password is False
    assert user.password_hash != old_hash
    assert verify_password("NewDummyPass123!", user.password_hash) is True
    assert verify_password("DummyPass123!", user.password_hash) is False
    _assert_no_password_material(response.model_dump_json())


def test_change_own_password_rejects_invalid_current_password(db_session: Session):
    user = _create_user(db_session)

    response = change_own_password(
        db_session,
        user.id,
        _request(current_password="WrongPass123!"),
    )

    assert response.success is False
    assert response.result_code == "INVALID_CURRENT_PASSWORD"


def test_change_own_password_rejects_confirm_mismatch(db_session: Session):
    user = _create_user(db_session)

    response = change_own_password(
        db_session,
        user.id,
        _request(new_password_confirm="MismatchPass123!"),
    )

    assert response.success is False
    assert response.result_code == "PASSWORD_CONFIRM_MISMATCH"


def test_change_own_password_rejects_short_password(db_session: Session):
    user = _create_user(db_session)

    response = change_own_password(
        db_session,
        user.id,
        _request(new_password="short", new_password_confirm="short"),
    )

    assert response.success is False
    assert response.result_code == "PASSWORD_POLICY_FAILED"


def test_change_own_password_rejects_inactive_user(db_session: Session):
    user = _create_user(db_session, active_yn=False)

    response = change_own_password(db_session, user.id, _request())

    assert response.success is False
    assert response.result_code == "INACTIVE_USER"


def test_change_own_password_rejects_missing_user(db_session: Session):
    response = change_own_password(db_session, 404, _request())

    assert response.success is False
    assert response.result_code == "USER_NOT_FOUND"
    _assert_no_password_material(response.model_dump_json())
