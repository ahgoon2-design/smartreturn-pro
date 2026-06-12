from app.seed.roles_permissions import (
    get_permission_seed_data,
    get_role_permission_seed_data,
    get_role_seed_data,
)


EXPECTED_ROLES = {
    "SUPER_ADMIN",
    "INTERNAL_ADMIN",
    "INTERNAL_WORKER",
    "AGENCY_ADMIN",
    "CLIENT_ADMIN",
    "CLIENT_USER",
    "READ_ONLY",
}

WRITE_PERMISSIONS = {
    "SYSTEM_ADMIN",
    "USER_MANAGE",
    "ROLE_MANAGE",
    "MASTER_MANAGE",
    "CLIENT_MANAGE",
    "WAREHOUSE_MANAGE",
    "PRODUCT_MANAGE",
    "COMMON_CODE_MANAGE",
    "IMPORT_MANAGE",
    "RETURN_CLIENT_SUBMIT",
    "RETURN_PREPARE",
    "RETURN_PROCESS",
    "RETURN_JUDGE",
    "RETURN_CLOSE",
    "RETURN_OUTBOUND",
    "INBOUND_PROCESS",
    "INBOUND_CONFIRM",
    "OUTBOUND_PROCESS",
    "OUTBOUND_CONFIRM",
    "INVENTORY_ADJUST",
    "SETTLEMENT_MANAGE",
    "LOCAL_AGENT_MANAGE",
}

INTERNAL_WORKER_FORBIDDEN = {
    "USER_MANAGE",
    "SYSTEM_ADMIN",
    "ROLE_MANAGE",
    "INVENTORY_ADJUST",
    "SETTLEMENT_MANAGE",
    "COMMON_CODE_MANAGE",
}

CLIENT_INTERNAL_OPERATION_FORBIDDEN = {
    "RETURN_PREPARE",
    "RETURN_PROCESS",
    "RETURN_JUDGE",
    "RETURN_CLOSE",
    "RETURN_OUTBOUND",
}


def test_seed_roles_include_standard_roles() -> None:
    role_codes = {str(role["role_code"]) for role in get_role_seed_data()}

    assert role_codes == EXPECTED_ROLES


def test_role_permission_mapping_references_existing_codes() -> None:
    role_codes = {str(role["role_code"]) for role in get_role_seed_data()}
    permission_codes = {str(permission["permission_code"]) for permission in get_permission_seed_data()}

    mappings = get_role_permission_seed_data()

    assert set(mappings) == role_codes
    for mapped_permissions in mappings.values():
        assert set(mapped_permissions).issubset(permission_codes)


def test_super_admin_receives_all_permissions() -> None:
    permission_codes = {str(permission["permission_code"]) for permission in get_permission_seed_data()}
    mappings = get_role_permission_seed_data()

    assert set(mappings["SUPER_ADMIN"]) == permission_codes


def test_read_only_has_no_write_permissions() -> None:
    mappings = get_role_permission_seed_data()

    assert set(mappings["READ_ONLY"]).isdisjoint(WRITE_PERMISSIONS)


def test_internal_worker_does_not_receive_admin_permissions() -> None:
    mappings = get_role_permission_seed_data()

    assert set(mappings["INTERNAL_WORKER"]).isdisjoint(INTERNAL_WORKER_FORBIDDEN)


def test_client_roles_receive_portal_submit_without_internal_return_permissions() -> None:
    mappings = get_role_permission_seed_data()

    for role_code in ("CLIENT_ADMIN", "CLIENT_USER"):
        role_permissions = set(mappings[role_code])
        assert "RETURN_VIEW" in role_permissions
        assert "RETURN_CLIENT_SUBMIT" in role_permissions
        assert role_permissions.isdisjoint(CLIENT_INTERNAL_OPERATION_FORBIDDEN)
