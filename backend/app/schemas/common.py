"""공통 API 응답 schema."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ApiResult(BaseModel):
    success: bool
    result_code: str
    message: str
    data: Any = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[dict[str, Any] | str] = Field(default_factory=list)
    next_action: str | None = None
    request_id: str | None = None
    sound_code: str | None = None


def api_success(
    *,
    result_code: str = "OK",
    message: str = "처리되었습니다.",
    data: Any = None,
    warnings: list[str] | None = None,
    next_action: str | None = None,
) -> ApiResult:
    return ApiResult(
        success=True,
        result_code=result_code,
        message=message,
        data=data,
        warnings=warnings or [],
        next_action=next_action,
    )


def api_error(
    *,
    result_code: str,
    message: str,
    errors: list[dict[str, Any] | str] | None = None,
    next_action: str | None = None,
) -> ApiResult:
    return ApiResult(
        success=False,
        result_code=result_code,
        message=message,
        data=None,
        warnings=[],
        errors=errors or [],
        next_action=next_action,
    )
