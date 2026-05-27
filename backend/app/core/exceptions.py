"""인증과 권한 검증에서 사용할 공통 예외."""

from __future__ import annotations


class AuthError(Exception):
    """인증/권한 계열 공통 예외."""

    result_code = "AUTH_ERROR"
    message = "인증 또는 권한 검증에 실패했습니다."
    status_code = 403

    def __init__(
        self,
        message: str | None = None,
        *,
        result_code: str | None = None,
        status_code: int | None = None,
    ) -> None:
        self.message = message or self.message
        self.result_code = result_code or self.result_code
        self.status_code = status_code or self.status_code
        super().__init__(self.message)


class NotAuthenticatedError(AuthError):
    result_code = "NOT_AUTHENTICATED"
    message = "인증이 필요합니다."
    status_code = 401


class PermissionDeniedError(AuthError):
    result_code = "PERMISSION_DENIED"
    message = "권한이 없습니다."
    status_code = 403


class ClientScopeDeniedError(AuthError):
    result_code = "CLIENT_SCOPE_DENIED"
    message = "고객사 접근 범위가 아닙니다."
    status_code = 403


class WarehouseScopeDeniedError(AuthError):
    result_code = "WAREHOUSE_SCOPE_DENIED"
    message = "창고 접근 범위가 아닙니다."
    status_code = 403


class PasswordChangeRequiredError(AuthError):
    result_code = "PASSWORD_CHANGE_REQUIRED"
    message = "비밀번호 변경 후 이용할 수 있습니다."
    status_code = 403
