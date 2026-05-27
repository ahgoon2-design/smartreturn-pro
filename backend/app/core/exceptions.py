"""인증과 권한 검증에 사용하는 공통 예외."""

from __future__ import annotations


class AuthError(Exception):
    """인증/권한 계열 공통 예외."""

    result_code = "AUTH_ERROR"
    message = "인증 또는 권한 검증에 실패했습니다."
    status_code = 403
    next_action: str | None = None

    def __init__(
        self,
        message: str | None = None,
        *,
        result_code: str | None = None,
        status_code: int | None = None,
        next_action: str | None = None,
    ) -> None:
        self.message = message or self.message
        self.result_code = result_code or self.result_code
        self.status_code = status_code or self.status_code
        self.next_action = next_action if next_action is not None else self.next_action
        super().__init__(self.message)


class NotAuthenticatedError(AuthError):
    result_code = "NOT_AUTHENTICATED"
    message = "인증이 필요합니다."
    status_code = 401


class InvalidTokenError(NotAuthenticatedError):
    result_code = "INVALID_TOKEN"
    message = "유효하지 않은 인증 토큰입니다."
    status_code = 401


class InvalidLoginError(NotAuthenticatedError):
    result_code = "INVALID_LOGIN"
    message = "아이디 또는 비밀번호가 올바르지 않습니다."
    status_code = 401


class TokenExpiredError(NotAuthenticatedError):
    result_code = "TOKEN_EXPIRED"
    message = "인증 토큰이 만료되었습니다."
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
    next_action = "CHANGE_PASSWORD"
