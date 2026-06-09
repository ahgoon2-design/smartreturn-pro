"""로그인과 AuthContext 구성 service skeleton."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.auth_context import build_auth_context_from_user
from app.core.config import get_settings
from app.core.exceptions import InvalidLoginError, NotAuthenticatedError
from app.core.jwt import create_access_token
from app.core.security import verify_password
from app.models.auth import Permission, Role, RolePermission, User, UserRole
from app.models.master import Agency, Client
from app.schemas.auth import AuthContext
from app.schemas.login import LoginRequest, LoginResponse, LoginUserDto


def _get_role_codes(db: Session, user_id: int) -> list[str]:
    rows = (
        db.query(Role.role_code)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user_id, Role.active_yn.is_(True))
        .all()
    )
    return sorted({row[0] for row in rows})


def _get_permission_codes(db: Session, user_id: int) -> list[str]:
    rows = (
        db.query(Permission.permission_code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(
            UserRole.user_id == user_id,
            Role.active_yn.is_(True),
            Permission.active_yn.is_(True),
        )
        .all()
    )
    return sorted({row[0] for row in rows})


def _get_client(db: Session, client_id: int | None) -> Client | None:
    if client_id is None:
        return None
    return db.query(Client).filter(Client.id == client_id).one_or_none()


def _get_agency(db: Session, agency_id: int | None) -> Agency | None:
    if agency_id is None:
        return None
    return db.query(Agency).filter(Agency.id == agency_id).one_or_none()


def _get_agency_client_ids(db: Session, agency_id: int | None) -> list[int]:
    if agency_id is None:
        return []
    rows = db.query(Client.id).filter(Client.agency_id == agency_id, Client.active_yn.is_(True)).all()
    return [row[0] for row in rows]


def authenticate_user(db: Session, login_id: str, password: str) -> User | None:
    user = db.query(User).filter(User.login_id == login_id).one_or_none()
    if user is None or not user.active_yn:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_user_auth_context(db: Session, user_id: int) -> AuthContext:
    user = db.query(User).filter(User.id == user_id).one_or_none()
    if user is None or not user.active_yn:
        raise NotAuthenticatedError("인증된 사용자를 찾을 수 없습니다.")

    client = _get_client(db, user.client_id)
    agency = _get_agency(db, user.agency_id)
    return build_auth_context_from_user(
        user,
        roles=_get_role_codes(db, user.id),
        permissions=_get_permission_codes(db, user.id),
        client_code=client.client_code if client else None,
        client_name=client.client_name if client else None,
        agency_name=agency.agency_name if agency else None,
        allowed_client_ids=_get_agency_client_ids(db, user.agency_id),
    )


def login(db: Session, request: LoginRequest) -> LoginResponse:
    user = authenticate_user(db, request.login_id, request.password)
    if user is None:
        raise InvalidLoginError()

    auth = get_user_auth_context(db, user.id)
    user.last_login_at = datetime.now(UTC)
    db.commit()

    settings = get_settings()
    access_token = create_access_token(str(user.id), settings.access_token_expire_minutes)
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        must_change_password=auth.must_change_password,
        user=LoginUserDto(
            user_id=auth.user_id,
            login_id=auth.login_id,
            user_name=auth.user_name,
            roles=auth.roles,
            client_id=auth.client_id,
            agency_id=auth.agency_id,
            agency_name=auth.agency_name,
            client_name=auth.client_name,
            must_change_password=auth.must_change_password,
        ),
        result_code="LOGIN_SUCCESS",
        message="로그인되었습니다.",
    )
