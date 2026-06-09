import pytest

from app.core.exceptions import (
    ClientScopeDeniedError,
    PasswordChangeRequiredError,
    PermissionDeniedError,
    WarehouseScopeDeniedError,
)
from app.core.permissions import (
    can_access_client,
    can_select_client,
    can_select_client_for_user,
    can_write,
    require_any_permission,
    require_client_access,
    require_password_change_completed,
    require_permission,
    require_roles,
    require_warehouse_access,
)
from app.schemas.auth import AuthContext


def _auth(**overrides) -> AuthContext:
    data = {
        "user_id": 1,
        "login_id": "tester",
        "user_name": "테스터",
        "roles": ["INTERNAL_WORKER"],
        "permissions": ["RETURN_VIEW"],
        "client_id": None,
        "must_change_password": False,
        "is_internal_user": True,
        "is_client_user": False,
    }
    data.update(overrides)
    return AuthContext(**data)


def test_require_roles_success_and_failure():
    require_roles(_auth(roles=["INTERNAL_WORKER"]), {"INTERNAL_WORKER"})

    with pytest.raises(PermissionDeniedError):
        require_roles(_auth(roles=["CLIENT_USER"], is_internal_user=False, is_client_user=True), {"INTERNAL_WORKER"})


def test_require_permission_success_and_failure():
    require_permission(_auth(permissions=["RETURN_VIEW"]), "RETURN_VIEW")

    with pytest.raises(PermissionDeniedError):
        require_permission(_auth(permissions=["RETURN_VIEW"]), "RETURN_JUDGE")


def test_super_admin_passes_permission_check():
    auth = _auth(roles=["SUPER_ADMIN"], permissions=[])

    require_permission(auth, "SYSTEM_ADMIN")
    require_any_permission(auth, {"INVENTORY_ADJUST"})


def test_require_any_permission_success_and_failure():
    require_any_permission(_auth(permissions=["RETURN_VIEW", "RETURN_TRACE"]), {"RETURN_TRACE", "RETURN_JUDGE"})

    with pytest.raises(PermissionDeniedError):
        require_any_permission(_auth(permissions=["RETURN_VIEW"]), {"RETURN_JUDGE"})


def test_password_change_required_blocks_business_api():
    with pytest.raises(PasswordChangeRequiredError):
        require_password_change_completed(_auth(must_change_password=True))


def test_client_scope_blocks_other_client():
    auth = _auth(
        roles=["CLIENT_USER"],
        client_id=10,
        is_internal_user=False,
        is_client_user=True,
    )

    require_client_access(auth, 10)
    with pytest.raises(ClientScopeDeniedError):
        require_client_access(auth, 11)


def test_internal_user_passes_client_scope():
    require_client_access(_auth(roles=["INTERNAL_ADMIN"], is_internal_user=True), 99)


def test_agency_user_does_not_get_all_client_scope_before_mapping_exists():
    auth = _auth(
        roles=["AGENCY_ADMIN"],
        is_internal_user=False,
        is_agency_user=True,
        is_client_user=False,
    )

    with pytest.raises(ClientScopeDeniedError):
        require_client_access(auth, 99)
    assert can_access_client(auth, 99) is False


def test_warehouse_scope_blocks_not_allowed_warehouse():
    auth = _auth()

    require_warehouse_access(auth, {1, 2}, 1)
    with pytest.raises(WarehouseScopeDeniedError):
        require_warehouse_access(auth, {1, 2}, 3)


def test_can_select_client_and_can_write():
    assert can_select_client(_auth(is_internal_user=True)) is True
    assert can_select_client_for_user(_auth(is_internal_user=True)) is True
    assert can_select_client(_auth(is_internal_user=False, is_client_user=True)) is False
    assert can_select_client(_auth(roles=["AGENCY_ADMIN"], is_internal_user=False, is_agency_user=True)) is False
    assert can_write(_auth(roles=["READ_ONLY"])) is False
    assert can_write(_auth(must_change_password=True)) is False
    assert can_write(_auth()) is True
