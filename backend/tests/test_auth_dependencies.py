from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.dependencies import get_current_auth_context, get_current_user
from app.core.exceptions import InvalidTokenError, PasswordChangeRequiredError
from app.core.jwt import create_access_token, decode_access_token
from app.core.permissions import require_password_change_completed
from app.core.security import hash_password
from app.models.auth import Permission, Role, RolePermission, User, UserRole
from app.models.master import Client, Warehouse
from app.schemas.auth import AuthContext


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
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


def _create_user(db: Session, *, must_change_password: bool = False) -> User:
    role = Role(
        role_code="INTERNAL_ADMIN",
        role_name="내부 관리자",
        role_type="INTERNAL",
        active_yn=True,
    )
    permission = Permission(
        permission_code="MASTER_VIEW",
        permission_name="기준정보 조회",
        description="테스트용 권한",
        active_yn=True,
    )
    user = User(
        login_id="tester",
        user_name="테스트",
        password_hash=hash_password("DummyPass123!"),
        active_yn=True,
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


def test_access_token_round_trip():
    token = create_access_token("123", expires_delta_minutes=5)
    payload = decode_access_token(token)

    assert payload["sub"] == "123"
    assert payload["type"] == "access"


def test_invalid_token_decode_fails():
    with pytest.raises(Exception):
        decode_access_token("not-a-token")


def test_get_current_auth_context_contains_roles_and_permissions(db_session: Session):
    user = _create_user(db_session)
    token = create_access_token(str(user.id))

    current_user = get_current_user(token, db_session)
    auth = get_current_auth_context(current_user, db_session)

    assert auth.user_id == user.id
    assert auth.roles == ["INTERNAL_ADMIN"]
    assert auth.permissions == ["MASTER_VIEW"]


def test_invalid_token_dependency_fails(db_session: Session):
    with pytest.raises(InvalidTokenError) as exc:
        get_current_user("bad-token", db_session)

    assert exc.value.result_code == "INVALID_TOKEN"


def test_must_change_password_user_can_have_context(db_session: Session):
    user = _create_user(db_session, must_change_password=True)
    token = create_access_token(str(user.id))

    current_user = get_current_user(token, db_session)
    auth = get_current_auth_context(current_user, db_session)

    assert auth.must_change_password is True


def test_password_change_completed_dependency_blocks_required_user():
    auth = AuthContext(
        user_id=1,
        login_id="tester",
        user_name="테스트",
        roles=["INTERNAL_ADMIN"],
        permissions=[],
        must_change_password=True,
        is_internal_user=True,
    )

    with pytest.raises(PasswordChangeRequiredError):
        require_password_change_completed(auth)
