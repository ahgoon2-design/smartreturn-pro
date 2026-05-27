"""비밀번호 변경 API skeleton."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.password import ChangePasswordRequest, ChangePasswordResponse
from app.services.password_service import change_own_password


router = APIRouter(prefix="/api/auth/password", tags=["auth-password"])


@router.post("/change", response_model=ChangePasswordResponse)
def change_password(
    request: ChangePasswordRequest,
    # 운영 전 JWT/AuthContext dependency로 반드시 교체해야 하는 테스트용 헤더다.
    x_test_user_id: Annotated[int | None, Header(alias="X-Test-User-Id")] = None,
    db: Session = Depends(get_db),
) -> ChangePasswordResponse:
    if x_test_user_id is None:
        raise HTTPException(
            status_code=401,
            detail={
                "result_code": "NOT_AUTHENTICATED",
                "message": "인증된 사용자 정보가 필요합니다.",
            },
        )

    return change_own_password(db, x_test_user_id, request)
