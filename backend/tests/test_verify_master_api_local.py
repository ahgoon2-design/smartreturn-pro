from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = BACKEND_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from _local_config import LocalApiConfig, LocalAuthConfig, LocalDatabaseConfig, LocalSecretConfig  # noqa: E402
from verify_master_api_local import (  # noqa: E402
    _run_client_warehouses_check,
    _run_login_flow,
)


def _config() -> LocalSecretConfig:
    return LocalSecretConfig(
        environment="local",
        api=LocalApiConfig(base_url="http://testserver"),
        database=LocalDatabaseConfig(url=None),
        auth=LocalAuthConfig(
            admin_login_id="local_super_admin",
            current_password="dummy-current-password",
            new_password="dummy-new-password",
        ),
        source_path=Path("local.secret.json"),
    )


def _json_response(status_code: int, payload: dict) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=payload,
        headers={"content-type": "application/json"},
    )


def _request_json(request: httpx.Request) -> dict:
    return json.loads(request.content.decode("utf-8"))


def test_login_flow_changes_password_when_current_password_login_succeeds() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/login":
            password = _request_json(request)["password"]
            calls.append(f"login:{password}")
            return _json_response(
                200,
                {"access_token": f"token-for-{password}", "token_type": "bearer"},
            )
        if request.url.path == "/api/auth/password/change":
            calls.append("password_change")
            return _json_response(
                200,
                {
                    "success": True,
                    "result_code": "PASSWORD_CHANGED",
                    "must_change_password": False,
                },
            )
        raise AssertionError(f"unexpected path: {request.url.path}")

    client = httpx.Client(base_url="http://testserver", transport=httpx.MockTransport(handler))

    result = _run_login_flow(client, _config())

    assert result.token == "token-for-dummy-new-password"
    assert calls == [
        "login:dummy-current-password",
        "password_change",
        "login:dummy-new-password",
    ]
    assert [item.name for item in result.results] == [
        "login_current_password",
        "password_change",
        "login_new_password",
    ]


def test_login_flow_falls_back_to_new_password_after_invalid_login() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        password = _request_json(request)["password"]
        calls.append(f"login:{password}")
        if password == "dummy-current-password":
            return _json_response(
                401,
                {"success": False, "result_code": "INVALID_LOGIN"},
            )
        return _json_response(
            200,
            {"access_token": "token-after-reset", "token_type": "bearer"},
        )

    client = httpx.Client(base_url="http://testserver", transport=httpx.MockTransport(handler))

    result = _run_login_flow(client, _config())

    assert result.token == "token-after-reset"
    assert calls == ["login:dummy-current-password", "login:dummy-new-password"]
    assert [item.name for item in result.results] == [
        "login_current_password",
        "login_new_password_fallback",
        "password_change",
    ]
    assert result.results[-1].ok is True
    assert "skipped=already_reset_state" in result.results[-1].detail


def test_login_flow_fails_when_both_passwords_fail() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(
            401,
            {"success": False, "result_code": "INVALID_LOGIN"},
        )

    client = httpx.Client(base_url="http://testserver", transport=httpx.MockTransport(handler))

    result = _run_login_flow(client, _config())

    assert result.token is None
    assert [item.name for item in result.results] == [
        "login_current_password",
        "login_new_password_fallback",
    ]
    assert all("dummy-" not in item.detail for item in result.results)


def test_client_warehouses_skips_when_client_id_candidate_is_missing() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("client-warehouses must not be called without client_id candidate")

    client = httpx.Client(base_url="http://testserver", transport=httpx.MockTransport(handler))

    result = _run_client_warehouses_check(client, "token", [])

    assert result.ok is True
    assert result.name == "/api/master/client-warehouses"
    assert "skipped=no_client_id_candidate" in result.detail


def test_client_warehouses_uses_client_id_candidate() -> None:
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        return _json_response(
            200,
            {
                "success": True,
                "result_code": "MASTER_CLIENT_WAREHOUSES_FOUND",
                "data": [],
            },
        )

    client = httpx.Client(base_url="http://testserver", transport=httpx.MockTransport(handler))

    result = _run_client_warehouses_check(client, "token", [{"client_id": 7}])

    assert result.ok is True
    assert requested_urls == ["http://testserver/api/master/client-warehouses?client_id=7"]
