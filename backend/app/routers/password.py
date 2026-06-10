"""비밀번호 변경 API skeleton."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_auth_context, get_db
from app.schemas.auth import AuthContext
from app.schemas.password import ChangePasswordRequest, ChangePasswordResponse
from app.services.password_service import change_own_password


router = APIRouter(prefix="/api/auth/password", tags=["auth-password"])


@router.post("/change", response_model=ChangePasswordResponse)
def change_password(
    request: ChangePasswordRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    db: Session = Depends(get_db),
) -> ChangePasswordResponse:
    # must_change_password=true 상태에서도 이 API는 호출 가능해야 한다.
    return change_own_password(db, auth.user_id, request)
