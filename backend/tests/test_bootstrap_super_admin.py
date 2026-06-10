from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.auth import Role, User, UserRole
from app.models.master import Client, Warehouse
from app.seed.super_admin import bootstrap_super_admin


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


def _add_super_admin_role(db: Session) -> Role:
    role = Role(
        role_code="SUPER_ADMIN",
        role_name="최고 관리자",
        role_type="INTERNAL",
        active_yn=True,
    )
    db.add(role)
    db.commit()
    return role


def _assert_no_password_material(result: dict, plain_password: str) -> None:
    result_text = str(result)
    assert plain_password not in result_text
    assert "password_hash" not in result
    assert "plain_password" not in result


def test_bootstrap_requires_seeded_super_admin_role(db_session: Session):
    plain_password = "DummyPass123!"

    result = bootstrap_super_admin(
        db_session,
        login_id="admin",
        user_name="최고 관리자",
        plain_password=plain_password,
    )

    assert result["result_code"] == "ROLE_NOT_SEEDED"
    assert db_session.query(User).count() == 0
    _assert_no_password_material(result, plain_password)


def test_bootstrap_creates_super_admin_user(db_session: Session):
    plain_password = "DummyPass123!"
    role = _add_super_admin_role(db_session)

    result = bootstrap_super_admin(
        db_session,
        login_id="admin",
        user_name="최고 관리자",
        plain_password=plain_password,
    )

    assert result["result_code"] == "CREATED"
    _assert_no_password_material(result, plain_password)

    user = db_session.query(User).filter(User.login_id == "admin").one()
    assert user.must_change_password is True
    assert user.active_yn is True
    assert user.password_hash != plain_password

    user_role = db_session.query(UserRole).one()
    assert user_role.user_id == user.id
    assert user_role.role_id == role.id


def test_bootstrap_does_not_create_when_super_admin_exists(db_session: Session):
    role = _add_super_admin_role(db_session)
    existing_user = User(
        login_id="existing-admin",
        user_name="기존 관리자",
        password_hash="already-hashed",
        must_change_password=True,
        active_yn=True,
    )
    db_session.add(existing_user)
    db_session.flush()
    db_session.add(UserRole(user_id=existing_user.id, role_id=role.id))
    db_session.commit()

    result = bootstrap_super_admin(
        db_session,
        login_id="new-admin",
        user_name="새 관리자",
        plain_password="DummyPass123!",
    )

    assert result["result_code"] == "SUPER_ADMIN_EXISTS"
    assert db_session.query(User).count() == 1


def test_bootstrap_does_not_create_duplicate_login_id(db_session: Session):
    _add_super_admin_role(db_session)
    db_session.add(
        User(
            login_id="admin",
            user_name="기존 사용자",
            password_hash="already-hashed",
            must_change_password=False,
            active_yn=True,
        )
    )
    db_session.commit()

    result = bootstrap_super_admin(
        db_session,
        login_id="admin",
        user_name="최고 관리자",
        plain_password="DummyPass123!",
    )

    assert result["result_code"] == "ALREADY_EXISTS"
    assert db_session.query(User).count() == 1


def test_bootstrap_rejects_password_same_as_login_id(db_session: Session):
    plain_password = "admin1234"
    _add_super_admin_role(db_session)

    result = bootstrap_super_admin(
        db_session,
        login_id="admin1234",
        user_name="최고 관리자",
        plain_password=plain_password,
    )

    assert result["result_code"] == "PASSWORD_POLICY_FAILED"
    assert db_session.query(User).count() == 0
    _assert_no_password_material(result, plain_password)
