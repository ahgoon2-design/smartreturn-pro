"""AuthContext 구성과 role/client scope 해석 유틸."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.core.exceptions import ClientScopeDeniedError, PermissionDeniedError
from app.models.auth import User
from app.schemas.auth import AuthContext


PLATFORM_ADMIN_ROLES = {"SUPER_ADMIN", "INTERNAL_ADMIN"}
INTERNAL_ROLES = PLATFORM_ADMIN_ROLES | {"INTERNAL_WORKER"}
AGENCY_ROLES = {"AGENCY_ADMIN"}
CLIENT_ROLES = {"CLIENT_ADMIN", "CLIENT_USER", "READ_ONLY"}


def is_platform_admin_role(role_code: str) -> bool:
    return role_code in PLATFORM_ADMIN_ROLES


def is_internal_role(role_code: str) -> bool:
    return role_code in INTERNAL_ROLES


def is_agency_role(role_code: str) -> bool:
    return role_code in AGENCY_ROLES


def is_client_role(role_code: str) -> bool:
    return role_code in CLIENT_ROLES


def has_any_role(roles: list[str], required_roles: set[str]) -> bool:
    return bool(set(roles) & required_roles)


def _extract_codes(values: Iterable[Any] | None, code_attr: str) -> list[str]:
    codes: list[str] = []
    for value in values or []:
        if isinstance(value, str):
            codes.append(value)
        else:
            code = getattr(value, code_attr, None)
            if code:
                codes.append(str(code))
    return sorted(set(codes))


def build_auth_context_from_user(
    user: User,
    *,
    roles: Iterable[str] | None = None,
    permissions: Iterable[str] | None = None,
    client_code: str | None = None,
    client_name: str | None = None,
    selected_client_id: int | None = None,
    effective_client_id: int | None = None,
) -> AuthContext:
    """User와 사전 조회된 role/permission 코드로 AuthContext를 만든다."""

    role_values = roles
    if role_values is None:
        role_values = getattr(user, "role_codes", None) or getattr(user, "roles", None)

    permission_values = permissions
    if permission_values is None:
        permission_values = getattr(user, "permission_codes", None) or getattr(user, "permissions", None)

    role_codes = _extract_codes(role_values, "role_code")
    permission_codes = _extract_codes(permission_values, "permission_code")

    if not role_codes:
        raise PermissionDeniedError("사용자에게 role이 없어 업무 API에 접근할 수 없습니다.")

    is_platform_admin = has_any_role(role_codes, PLATFORM_ADMIN_ROLES)
    is_internal_user = has_any_role(role_codes, INTERNAL_ROLES)
    is_agency_user = not is_internal_user and has_any_role(role_codes, AGENCY_ROLES)
    is_client_user = not is_internal_user and not is_agency_user and has_any_role(role_codes, CLIENT_ROLES)
    client_id = getattr(user, "client_id", None)
    agency_id = getattr(user, "agency_id", None)

    if is_client_user and client_id is None:
        raise ClientScopeDeniedError("고객사 사용자는 client_id가 필요합니다.")

    allowed_client_ids = [client_id] if is_client_user and client_id is not None else []
    auth = AuthContext(
        user_id=user.id,
        login_id=user.login_id,
        user_name=user.user_name,
        roles=role_codes,
        permissions=permission_codes,
        client_id=client_id,
        agency_id=agency_id,
        client_code=client_code,
        client_name=client_name,
        default_warehouse_id=getattr(user, "default_warehouse_id", None),
        must_change_password=bool(getattr(user, "must_change_password", False)),
        is_platform_admin=is_platform_admin,
        is_internal_user=is_internal_user,
        is_agency_user=is_agency_user,
        is_client_user=is_client_user,
        allowed_client_ids=allowed_client_ids,
        selected_client_id=selected_client_id,
        effective_client_id=effective_client_id,
    )

    if auth.is_client_user and auth.effective_client_id is None:
        auth.effective_client_id = auth.client_id
    return auth


def resolve_effective_client_id(
    auth: AuthContext,
    requested_client_id: int | None,
    *,
    allow_all_clients: bool = False,
) -> int | None:
    """요청 client_id와 AuthContext로 최종 client scope를 결정한다."""

    if auth.is_internal_user:
        if requested_client_id is not None:
            return requested_client_id
        if allow_all_clients:
            return None
        raise ClientScopeDeniedError("이 API는 고객사 선택이 필요합니다.")

    if auth.is_client_user:
        if auth.client_id is None:
            raise ClientScopeDeniedError("고객사 사용자는 client_id가 필요합니다.")
        if requested_client_id is not None and requested_client_id != auth.client_id:
            raise ClientScopeDeniedError("다른 고객사 데이터에는 접근할 수 없습니다.")
        return auth.client_id

    if auth.is_agency_user:
        raise ClientScopeDeniedError("AGENCY_ADMIN client scope requires agency-client mapping.")

    raise PermissionDeniedError("알 수 없는 role 조합입니다.")
