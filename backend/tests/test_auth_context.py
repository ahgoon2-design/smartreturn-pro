from types import SimpleNamespace

import pytest

from app.core.auth_context import (
    build_auth_context_from_user,
    is_client_role,
    is_internal_role,
    resolve_effective_client_id,
)
from app.core.exceptions import ClientScopeDeniedError


def _user(**overrides):
    data = {
        "id": 1,
        "login_id": "tester",
        "user_name": "테스터",
        "client_id": None,
        "default_warehouse_id": None,
        "must_change_password": False,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


@pytest.mark.parametrize("role_code", ["SUPER_ADMIN", "INTERNAL_ADMIN", "INTERNAL_WORKER"])
def test_internal_roles_are_internal(role_code: str):
    auth = build_auth_context_from_user(_user(client_id=10), roles=[role_code])

    assert is_internal_role(role_code) is True
    assert auth.is_internal_user is True
    assert auth.is_client_user is False


@pytest.mark.parametrize("role_code", ["CLIENT_ADMIN", "CLIENT_USER", "READ_ONLY"])
def test_client_roles_are_client_users(role_code: str):
    auth = build_auth_context_from_user(_user(client_id=10), roles=[role_code])

    assert is_client_role(role_code) is True
    assert auth.is_client_user is True
    assert auth.is_internal_user is False
    assert auth.allowed_client_ids == [10]


def test_internal_worker_with_client_id_is_not_client_user():
    auth = build_auth_context_from_user(_user(client_id=10), roles=["INTERNAL_WORKER"])

    assert auth.is_internal_user is True
    assert auth.is_client_user is False
    assert auth.allowed_client_ids == []


def test_client_effective_client_id_is_fixed_to_own_client():
    auth = build_auth_context_from_user(_user(client_id=10), roles=["CLIENT_USER"])

    assert resolve_effective_client_id(auth, requested_client_id=None) == 10
    assert resolve_effective_client_id(auth, requested_client_id=10) == 10


def test_client_requesting_other_client_is_denied():
    auth = build_auth_context_from_user(_user(client_id=10), roles=["CLIENT_USER"])

    with pytest.raises(ClientScopeDeniedError):
        resolve_effective_client_id(auth, requested_client_id=11)


def test_internal_user_can_use_requested_client_id():
    auth = build_auth_context_from_user(_user(), roles=["INTERNAL_ADMIN"])

    assert resolve_effective_client_id(auth, requested_client_id=20) == 20


def test_internal_user_can_use_all_scope_when_allowed():
    auth = build_auth_context_from_user(_user(), roles=["INTERNAL_ADMIN"])

    assert resolve_effective_client_id(auth, requested_client_id=None, allow_all_clients=True) is None


def test_client_user_without_client_id_is_denied():
    with pytest.raises(ClientScopeDeniedError):
        build_auth_context_from_user(_user(client_id=None), roles=["CLIENT_USER"])
