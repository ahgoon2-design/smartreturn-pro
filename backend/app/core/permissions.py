"""role, permission, client scope, warehouse scope 검증 유틸."""

from __future__ import annotations

from app.core.exceptions import (
    ClientScopeDeniedError,
    PasswordChangeRequiredError,
    PermissionDeniedError,
    WarehouseScopeDeniedError,
)
from app.schemas.auth import AuthContext


SUPER_ADMIN_ROLE = "SUPER_ADMIN"
READ_ONLY_ROLE = "READ_ONLY"


def require_roles(auth: AuthContext, allowed_roles: set[str]) -> None:
    if SUPER_ADMIN_ROLE in auth.roles:
        return
    if not (set(auth.roles) & allowed_roles):
        raise PermissionDeniedError("허용된 role이 아닙니다.")


def require_permission(auth: AuthContext, permission_code: str) -> None:
    if SUPER_ADMIN_ROLE in auth.roles:
        return
    if permission_code not in auth.permissions:
        raise PermissionDeniedError("필요한 permission이 없습니다.")


def require_any_permission(auth: AuthContext, permission_codes: set[str]) -> None:
    if SUPER_ADMIN_ROLE in auth.roles:
        return
    if not (set(auth.permissions) & permission_codes):
        raise PermissionDeniedError("필요한 permission이 없습니다.")


def require_password_change_completed(auth: AuthContext) -> None:
    if auth.must_change_password:
        raise PasswordChangeRequiredError()


def require_client_access(auth: AuthContext, target_client_id: int | None) -> None:
    if auth.is_internal_user:
        return
    if auth.is_agency_user:
        if auth.agency_id is None:
            raise ClientScopeDeniedError("대리점 사용자는 agency_id가 필요합니다.")
        if target_client_id is None:
            raise ClientScopeDeniedError("고객사 선택이 필요합니다.")
        if not auth.allowed_client_ids:
            raise ClientScopeDeniedError("대리점 사용자의 고객사 접근 목록을 확인할 수 없습니다.")
        if target_client_id not in auth.allowed_client_ids:
            raise ClientScopeDeniedError("대리점 범위를 벗어난 고객사 데이터에는 접근할 수 없습니다.")
        return
    if not auth.is_client_user or auth.client_id is None:
        raise ClientScopeDeniedError()
    if target_client_id is None or target_client_id != auth.client_id:
        raise ClientScopeDeniedError("다른 고객사 데이터에는 접근할 수 없습니다.")


def require_warehouse_access(
    auth: AuthContext,
    allowed_warehouse_ids: set[int],
    target_warehouse_id: int | None,
) -> None:
    if target_warehouse_id is None:
        raise WarehouseScopeDeniedError("창고 선택이 필요합니다.")
    if target_warehouse_id not in allowed_warehouse_ids:
        raise WarehouseScopeDeniedError("허용된 창고가 아닙니다.")


def can_select_client(auth: AuthContext) -> bool:
    return auth.is_internal_user or auth.is_agency_user


def can_select_agency_for_user(auth: AuthContext) -> bool:
    return auth.is_internal_user


def can_access_agency(auth: AuthContext, target_agency_id: int | None) -> bool:
    if auth.is_internal_user:
        return True
    if target_agency_id is None:
        return False
    if auth.is_agency_user:
        return auth.agency_id == target_agency_id
    if auth.is_client_user:
        return auth.agency_id is None or auth.agency_id == target_agency_id
    return False


def can_select_client_for_user(auth: AuthContext) -> bool:
    return can_select_client(auth)


def can_access_client(auth: AuthContext, target_client_id: int | None) -> bool:
    try:
        require_client_access(auth, target_client_id)
    except ClientScopeDeniedError:
        return False
    return True


def can_write(auth: AuthContext) -> bool:
    # READ_ONLY는 조회 permission을 갖더라도 쓰기 API에서 별도 차단한다.
    return READ_ONLY_ROLE not in auth.roles and not auth.must_change_password
