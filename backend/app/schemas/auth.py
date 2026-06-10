"""인증된 사용자 컨텍스트 schema."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AuthContext(BaseModel):
    user_id: int
    login_id: str
    user_name: str
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    client_id: int | None = None
    client_unit_id: int | None = None
    agency_id: int | None = None
    agency_name: str | None = None
    client_code: str | None = None
    client_name: str | None = None
    default_warehouse_id: int | None = None
    must_change_password: bool = False
    is_platform_admin: bool = False
    is_internal_user: bool = False
    is_agency_user: bool = False
    is_client_user: bool = False
    allowed_client_ids: list[int] = Field(default_factory=list)
    selected_client_id: int | None = None
    effective_client_id: int | None = None
