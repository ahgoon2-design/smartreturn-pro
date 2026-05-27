"""인증/권한 예외를 공통 ApiResult 응답으로 변환한다."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.exceptions import AuthError
from app.schemas.common import api_error


def auth_error_to_response(exc: AuthError) -> JSONResponse:
    result = api_error(
        result_code=exc.result_code,
        message=exc.message,
        next_action=exc.next_action,
    )
    return JSONResponse(status_code=exc.status_code, content=result.model_dump())


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AuthError)
    async def handle_auth_error(_, exc: AuthError) -> JSONResponse:
        return auth_error_to_response(exc)
