"""FastAPI 인증 dependency skeleton."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError, InvalidTokenError, NotAuthenticatedError
from app.core.jwt import decode_access_token
from app.core.permissions import require_password_change_completed
from app.db.session import get_db as get_db
from app.models.auth import User
from app.schemas.auth import AuthContext
from app.services.auth_service import get_user_auth_context


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> User:
    if token is None:
        raise NotAuthenticatedError("인증 토큰이 필요합니다.")

    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (AuthError, TypeError, ValueError) as exc:
        if isinstance(exc, AuthError):
            raise exc
        raise InvalidTokenError() from exc

    user = db.query(User).filter(User.id == user_id).one_or_none()
    if user is None or not user.active_yn:
        raise NotAuthenticatedError("인증된 사용자를 찾을 수 없습니다.")
    return user


def get_current_auth_context(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuthContext:
    return get_user_auth_context(db, current_user.id)


def require_current_auth_context(
    auth: AuthContext = Depends(get_current_auth_context),
) -> AuthContext:
    return auth


def require_password_change_completed_dependency(
    auth: AuthContext = Depends(get_current_auth_context),
) -> AuthContext:
    require_password_change_completed(auth)
    return auth


def require_permission_dependency(permission_code: str):
    from app.core.permissions import require_permission

    def dependency(auth: AuthContext = Depends(get_current_auth_context)) -> AuthContext:
        require_permission(auth, permission_code)
        return auth

    return dependency
