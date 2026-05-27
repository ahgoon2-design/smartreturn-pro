"""로그인과 현재 인증 컨텍스트 API skeleton."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import auth_error_to_http_exception, get_current_auth_context, get_db
from app.core.exceptions import AuthError
from app.schemas.auth import AuthContext
from app.schemas.login import AuthContextResponse, LoginRequest, LoginResponse
from app.services.auth_service import login


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login_api(request: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    try:
        return login(db, request)
    except AuthError as exc:
        raise auth_error_to_http_exception(exc) from exc


@router.get("/context", response_model=AuthContextResponse)
def get_auth_context_api(auth: AuthContext = Depends(get_current_auth_context)) -> AuthContextResponse:
    return AuthContextResponse(
        user_id=auth.user_id,
        login_id=auth.login_id,
        user_name=auth.user_name,
        roles=auth.roles,
        permissions=auth.permissions,
        client_id=auth.client_id,
        client_name=auth.client_name,
        default_warehouse_id=auth.default_warehouse_id,
        must_change_password=auth.must_change_password,
        is_internal_user=auth.is_internal_user,
        is_client_user=auth.is_client_user,
        effective_client_id=auth.effective_client_id,
    )
