"""자기 비밀번호 변경 요청/응답 schema."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(repr=False)
    new_password: str = Field(repr=False)
    new_password_confirm: str = Field(repr=False)


class ChangePasswordResponse(BaseModel):
    success: bool
    result_code: str
    message: str
    must_change_password: bool | None = None
