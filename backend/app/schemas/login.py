"""로그인과 현재 인증 컨텍스트 응답 schema."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    login_id: str
    password: str = Field(repr=False)


class LoginUserDto(BaseModel):
    user_id: int
    login_id: str
    user_name: str
    roles: list[str] = Field(default_factory=list)
    client_id: int | None = None
    client_name: str | None = None
    must_change_password: bool


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    must_change_password: bool
    user: LoginUserDto
    result_code: str
    message: str


class AuthContextResponse(BaseModel):
    user_id: int
    login_id: str
    user_name: str
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    client_id: int | None = None
    client_name: str | None = None
    default_warehouse_id: int | None = None
    must_change_password: bool
    is_internal_user: bool
    is_client_user: bool
    effective_client_id: int | None = None
