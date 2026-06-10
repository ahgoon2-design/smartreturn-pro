"""자기 비밀번호 변경 service skeleton."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.security import hash_password, validate_password_policy, verify_password
from app.models.auth import User
from app.schemas.password import ChangePasswordRequest, ChangePasswordResponse


def _response(
    result_code: str,
    message: str,
    *,
    success: bool = False,
    must_change_password: bool | None = None,
) -> ChangePasswordResponse:
    return ChangePasswordResponse(
        success=success,
        result_code=result_code,
        message=message,
        must_change_password=must_change_password,
    )


def change_own_password(
    db: Session,
    user_id: int,
    request: ChangePasswordRequest,
) -> ChangePasswordResponse:
    """인증된 자기 계정의 비밀번호를 변경한다."""

    try:
        user = db.query(User).filter(User.id == user_id).one_or_none()
        if user is None:
            db.rollback()
            return _response("USER_NOT_FOUND", "사용자를 찾을 수 없습니다.")

        if not user.active_yn:
            db.rollback()
            return _response("INACTIVE_USER", "사용중지된 사용자입니다.")

        if not verify_password(request.current_password, user.password_hash):
            db.rollback()
            return _response("INVALID_CURRENT_PASSWORD", "현재 비밀번호가 올바르지 않습니다.")

        if request.new_password != request.new_password_confirm:
            db.rollback()
            return _response("PASSWORD_CONFIRM_MISMATCH", "새 비밀번호와 확인값이 다릅니다.")

        password_errors = validate_password_policy(request.new_password)
        if password_errors:
            db.rollback()
            return _response("PASSWORD_POLICY_FAILED", "새 비밀번호가 정책을 통과하지 못했습니다.")

        user.password_hash = hash_password(request.new_password)
        user.must_change_password = False
        user.updated_at = datetime.now(UTC)
        db.commit()

        return _response(
            "PASSWORD_CHANGED",
            "비밀번호가 변경되었습니다.",
            success=True,
            must_change_password=False,
        )
    except Exception:
        db.rollback()
        return _response("ERROR", "비밀번호 변경 처리 중 오류가 발생했습니다.")
