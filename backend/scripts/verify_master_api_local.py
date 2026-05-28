"""로컬 secret config 기반 P0 기준정보 read-only API 수동 검증 스크립트."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any

import httpx

from _local_config import LocalConfigError, LocalSecretConfig, load_local_secret_config


MASTER_ENDPOINTS = [
    "/api/master/clients",
    "/api/master/warehouses",
    "/api/master/products",
    "/api/master/common-code-groups",
    "/api/master/common-codes",
]

SENSITIVE_WORDS = [
    "password",
    "password_hash",
    "secret",
    "access_token",
    "traceback",
    "stack trace",
]


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


@dataclass
class LoginFlowResult:
    token: str | None
    results: list[CheckResult]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SmartReturn Pro 로컬 기준정보 read-only API 검증"
    )
    parser.add_argument(
        "--config",
        help="로컬 secret config 경로. 생략하면 SMARTRETURN_LOCAL_SECRET_FILE 또는 backend/local.secret.json을 사용한다.",
    )
    args = parser.parse_args()

    try:
        config = load_local_secret_config(args.config)
    except LocalConfigError as exc:
        _print_result(CheckResult("config", False, str(exc)))
        return 2

    print("SmartReturn Pro 로컬 기준정보 API 검증을 시작합니다.")
    print(f"- config: {config.source_path}")
    print(f"- api.base_url: {config.api.base_url}")
    print("- 전제: uvicorn 서버가 이미 실행 중이어야 합니다.")
    print("- 비밀번호와 access token 전체값은 출력하지 않습니다.")

    try:
        return _run_checks(config)
    except httpx.RequestError as exc:
        _print_result(
            CheckResult(
                "http",
                False,
                f"HTTP 요청에 실패했습니다. 서버 실행 여부와 base_url을 확인하세요. 오류 유형: {type(exc).__name__}",
            )
        )
        return 3


def _run_checks(config: LocalSecretConfig) -> int:
    with httpx.Client(base_url=config.api.base_url, timeout=10.0) as client:
        return _run_checks_with_client(config, client)


def _run_checks_with_client(config: LocalSecretConfig, client: httpx.Client) -> int:
    results: list[CheckResult] = []

    health_response = client.get("/health")
    results.append(_expect_status("health", health_response, 200))

    login_flow = _run_login_flow(client, config)
    results.extend(login_flow.results)
    if not login_flow.token:
        _print_results(results)
        return 1

    context_response = client.get("/api/auth/context", headers=_auth_header(login_flow.token))
    context_ok, _context_data = _parse_context(context_response)
    results.append(context_ok)

    endpoint_data: dict[str, Any] = {}
    for endpoint in MASTER_ENDPOINTS:
        response = client.get(endpoint, headers=_auth_header(login_flow.token))
        result, data = _parse_master_endpoint(endpoint, response)
        results.append(result)
        endpoint_data[endpoint] = data

    results.append(
        _run_client_warehouses_check(
            client,
            login_flow.token,
            endpoint_data.get("/api/master/clients"),
        )
    )
    results.extend(_run_detail_checks(client, login_flow.token, endpoint_data))
    results.extend(_run_error_checks(client))

    _print_results(results)
    return 0 if all(result.ok for result in results) else 1


def _run_login_flow(client: httpx.Client, config: LocalSecretConfig) -> LoginFlowResult:
    results: list[CheckResult] = []
    login_response = client.post(
        "/api/auth/login",
        json={
            "login_id": config.auth.admin_login_id,
            "password": config.auth.current_password,
        },
    )
    login_ok, token = _parse_login("login_current_password", login_response)
    results.append(login_ok)
    if token:
        change_response = client.post(
            "/api/auth/password/change",
            headers=_auth_header(token),
            json={
                "current_password": config.auth.current_password,
                "new_password": config.auth.new_password,
                "new_password_confirm": config.auth.new_password,
            },
        )
        results.append(_parse_password_change(change_response))
        if not _is_success_response(change_response):
            return LoginFlowResult(None, results)

        new_login_response = client.post(
            "/api/auth/login",
            json={
                "login_id": config.auth.admin_login_id,
                "password": config.auth.new_password,
            },
        )
        new_login_ok, new_token = _parse_login("login_new_password", new_login_response)
        results.append(new_login_ok)
        return LoginFlowResult(new_token, results)

    payload = _safe_json(login_response)
    if _result_code(payload) != "INVALID_LOGIN":
        return LoginFlowResult(None, results)

    fallback_response = client.post(
        "/api/auth/login",
        json={
            "login_id": config.auth.admin_login_id,
            "password": config.auth.new_password,
        },
    )
    fallback_ok, fallback_token = _parse_login("login_new_password_fallback", fallback_response)
    results.append(fallback_ok)
    if fallback_token:
        results.append(
            CheckResult(
                "password_change",
                True,
                "skipped=already_reset_state",
            )
        )
    return LoginFlowResult(fallback_token, results)


def _parse_login(name: str, response: httpx.Response) -> tuple[CheckResult, str | None]:
    payload = _safe_json(response)
    token = payload.get("access_token") if isinstance(payload, dict) else None
    token_type = payload.get("token_type") if isinstance(payload, dict) else None
    ok = response.status_code == 200 and isinstance(token, str) and token_type == "bearer"
    detail = f"status={response.status_code}, token_type={token_type or '-'}"
    if not ok:
        detail += f", result_code={_result_code(payload)}"
    return CheckResult(name, ok, detail), token if ok else None


def _parse_password_change(response: httpx.Response) -> CheckResult:
    payload = _safe_json(response)
    ok = (
        response.status_code == 200
        and isinstance(payload, dict)
        and payload.get("success") is True
        and payload.get("must_change_password") is False
    )
    must_change_password = payload.get("must_change_password") if isinstance(payload, dict) else "-"
    return CheckResult(
        "password_change",
        ok,
        f"status={response.status_code}, success={_success(payload)}, result_code={_result_code(payload)}, must_change_password={must_change_password}",
    )


def _parse_context(response: httpx.Response) -> tuple[CheckResult, dict[str, Any]]:
    payload = _safe_json(response)
    if not isinstance(payload, dict):
        return CheckResult("auth_context", False, f"status={response.status_code}, json=false"), {}

    roles = payload.get("roles") or []
    permissions = payload.get("permissions") or []
    ok = (
        response.status_code == 200
        and "SUPER_ADMIN" in roles
        and "MASTER_VIEW" in permissions
        and payload.get("is_internal_user") is True
        and payload.get("is_client_user") is False
        and payload.get("client_id") is None
        and payload.get("must_change_password") is False
    )
    detail = (
        f"status={response.status_code}, roles={roles}, "
        f"permissions_count={len(permissions)}, MASTER_VIEW={'MASTER_VIEW' in permissions}, "
        f"is_internal_user={payload.get('is_internal_user')}, "
        f"is_client_user={payload.get('is_client_user')}, "
        f"client_id={payload.get('client_id')}, "
        f"must_change_password={payload.get('must_change_password')}"
    )
    return CheckResult("auth_context", ok, detail), payload


def _parse_master_endpoint(endpoint: str, response: httpx.Response) -> tuple[CheckResult, Any]:
    payload = _safe_json(response)
    data = payload.get("data") if isinstance(payload, dict) else None
    ok = (
        response.status_code == 200
        and isinstance(payload, dict)
        and payload.get("success") is True
        and bool(payload.get("result_code"))
        and not _contains_sensitive_text(response.text)
    )
    detail = (
        f"status={response.status_code}, success={_success(payload)}, "
        f"result_code={_result_code(payload)}, data={_describe_data_shape(data)}"
    )
    return CheckResult(endpoint, ok, detail), data


def _run_detail_checks(
    client: httpx.Client,
    token: str,
    endpoint_data: dict[str, Any],
) -> list[CheckResult]:
    results: list[CheckResult] = []

    client_id = _first_id(endpoint_data.get("/api/master/clients"), "client_id")
    if client_id is None:
        results.append(CheckResult("/api/master/clients/{client_id}", True, "검증 가능한 상세 후보 없음"))
    else:
        response = client.get(f"/api/master/clients/{client_id}", headers=_auth_header(token))
        result, _ = _parse_master_endpoint(f"/api/master/clients/{client_id}", response)
        results.append(result)

    product_id = _first_id(endpoint_data.get("/api/master/products"), "product_id")
    if product_id is None:
        results.append(CheckResult("/api/master/products/{product_id}", True, "검증 가능한 상세 후보 없음"))
    else:
        response = client.get(f"/api/master/products/{product_id}", headers=_auth_header(token))
        result, _ = _parse_master_endpoint(f"/api/master/products/{product_id}", response)
        results.append(result)

    group_code = _first_id(endpoint_data.get("/api/master/common-code-groups"), "group_code")
    if group_code is None:
        results.append(CheckResult("/api/master/common-codes?group_code=...", True, "검증 가능한 group_code 없음"))
    else:
        response = client.get(
            "/api/master/common-codes",
            headers=_auth_header(token),
            params={"group_code": group_code},
        )
        result, _ = _parse_master_endpoint(f"/api/master/common-codes?group_code={group_code}", response)
        results.append(result)

    missing_product_response = client.get("/api/master/products/999999999", headers=_auth_header(token))
    missing_payload = _safe_json(missing_product_response)
    missing_ok = (
        missing_product_response.status_code in {404, 422}
        or (
            isinstance(missing_payload, dict)
            and missing_payload.get("success") is False
        )
    ) and not _contains_sensitive_text(missing_product_response.text)
    results.append(
        CheckResult(
            "/api/master/products/{missing_id}",
            missing_ok,
            f"status={missing_product_response.status_code}, result_code={_result_code(missing_payload)}",
        )
    )

    return results


def _run_client_warehouses_check(
    client: httpx.Client,
    token: str,
    clients_data: Any,
) -> CheckResult:
    client_id = _first_id(clients_data, "client_id")
    if client_id is None:
        return CheckResult(
            "/api/master/client-warehouses",
            True,
            "skipped=no_client_id_candidate",
        )

    response = client.get(
        "/api/master/client-warehouses",
        headers=_auth_header(token),
        params={"client_id": client_id},
    )
    result, _ = _parse_master_endpoint("/api/master/client-warehouses", response)
    return result


def _run_error_checks(client: httpx.Client) -> list[CheckResult]:
    results: list[CheckResult] = []

    no_auth_response = client.get("/api/master/clients")
    no_auth_payload = _safe_json(no_auth_response)
    results.append(
        CheckResult(
            "error_no_auth",
            no_auth_response.status_code == 401
            and isinstance(no_auth_payload, dict)
            and no_auth_payload.get("success") is False
            and no_auth_payload.get("result_code") == "NOT_AUTHENTICATED"
            and not _contains_sensitive_text(no_auth_response.text),
            f"status={no_auth_response.status_code}, result_code={_result_code(no_auth_payload)}",
        )
    )

    bad_token_response = client.get("/api/master/clients", headers=_auth_header("invalid-token"))
    bad_token_payload = _safe_json(bad_token_response)
    results.append(
        CheckResult(
            "error_invalid_token",
            bad_token_response.status_code == 401
            and isinstance(bad_token_payload, dict)
            and bad_token_payload.get("success") is False
            and bad_token_payload.get("result_code") == "INVALID_TOKEN"
            and not _contains_sensitive_text(bad_token_response.text),
            f"status={bad_token_response.status_code}, result_code={_result_code(bad_token_payload)}",
        )
    )

    return results


def _expect_status(name: str, response: httpx.Response, expected_status: int) -> CheckResult:
    payload = _safe_json(response)
    app_name = payload.get("app_name") if isinstance(payload, dict) else None
    status = payload.get("status") if isinstance(payload, dict) else None
    ok = response.status_code == expected_status
    if name == "health":
        ok = ok and status == "ok" and app_name == "SmartReturn Pro"
    return CheckResult(
        name,
        ok,
        f"status={response.status_code}, app_name={app_name or '-'}, health_status={status or '-'}",
    )


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def _result_code(payload: Any) -> str:
    if isinstance(payload, dict):
        value = payload.get("result_code")
        return str(value) if value is not None else "-"
    return "-"


def _success(payload: Any) -> str:
    if isinstance(payload, dict):
        return str(payload.get("success"))
    return "-"


def _is_success_response(response: httpx.Response) -> bool:
    payload = _safe_json(response)
    return response.status_code == 200 and isinstance(payload, dict) and payload.get("success") is True


def _describe_data_shape(data: Any) -> str:
    if isinstance(data, list):
        return f"list[{len(data)}]"
    if isinstance(data, dict):
        if isinstance(data.get("items"), list):
            return (
                "page("
                f"items={len(data['items'])}, "
                f"page={data.get('page')}, "
                f"page_size={data.get('page_size')}, "
                f"total_count={data.get('total_count')})"
            )
        return f"object[{','.join(sorted(data.keys()))}]"
    if data is None:
        return "null"
    return type(data).__name__


def _first_id(data: Any, key: str) -> Any:
    rows: list[Any]
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict) and isinstance(data.get("items"), list):
        rows = data["items"]
    else:
        return None

    for row in rows:
        if isinstance(row, dict) and row.get(key) is not None:
            return row[key]
    return None


def _contains_sensitive_text(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in SENSITIVE_WORDS)


def _print_result(result: CheckResult) -> None:
    status = "OK" if result.ok else "FAIL"
    print(f"[{status}] {result.name}: {result.detail}")


def _print_results(results: list[CheckResult]) -> None:
    for result in results:
        _print_result(result)
    total = len(results)
    passed = sum(1 for result in results if result.ok)
    print(f"검증 요약: {passed}/{total} 통과")


if __name__ == "__main__":
    raise SystemExit(main())
