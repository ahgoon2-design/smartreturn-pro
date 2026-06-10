"""로컬 검증 전용 secret config 로더.

이 모듈은 FastAPI 런타임 설정에 연결하지 않는다. 로컬 수동 검증 스크립트가
명시적으로 읽을 때만 사용한다.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCAL_SECRET_PATH = BACKEND_ROOT / "local.secret.json"
LOCAL_SECRET_FILE_ENV = "SMARTRETURN_LOCAL_SECRET_FILE"


class LocalConfigError(RuntimeError):
    """로컬 secret config를 안전하게 읽을 수 없을 때 발생한다."""


@dataclass(frozen=True)
class LocalApiConfig:
    base_url: str


@dataclass(frozen=True, repr=False)
class LocalDatabaseConfig:
    url: str | None = None

    def __repr__(self) -> str:
        return "LocalDatabaseConfig(url=<hidden>)"


@dataclass(frozen=True, repr=False)
class LocalAuthConfig:
    admin_login_id: str
    current_password: str
    new_password: str

    def __repr__(self) -> str:
        return (
            "LocalAuthConfig("
            f"admin_login_id={self.admin_login_id!r}, "
            "current_password=<hidden>, "
            "new_password=<hidden>)"
        )


@dataclass(frozen=True, repr=False)
class LocalSecretConfig:
    environment: str
    api: LocalApiConfig
    database: LocalDatabaseConfig
    auth: LocalAuthConfig
    source_path: Path

    def __repr__(self) -> str:
        return (
            "LocalSecretConfig("
            f"environment={self.environment!r}, "
            f"api={self.api!r}, "
            f"database={self.database!r}, "
            f"auth={self.auth!r}, "
            f"source_path={str(self.source_path)!r})"
        )


def resolve_local_secret_path(path: str | Path | None = None) -> Path:
    """명시 경로, 환경변수, 기본 경로 순서로 config 경로를 결정한다."""

    if path is not None:
        return Path(path).expanduser().resolve()

    env_path = os.getenv(LOCAL_SECRET_FILE_ENV)
    if env_path:
        return Path(env_path).expanduser().resolve()

    return DEFAULT_LOCAL_SECRET_PATH


def load_local_secret_config(
    path: str | Path | None = None,
    *,
    require_current_password: bool = True,
) -> LocalSecretConfig:
    """로컬 검증용 secret config를 읽고 필수 필드를 검증한다."""

    config_path = resolve_local_secret_path(path)
    if not config_path.exists():
        raise LocalConfigError(
            f"로컬 secret config 파일을 찾을 수 없습니다: {config_path}"
        )

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LocalConfigError("로컬 secret config JSON 형식이 올바르지 않습니다.") from exc

    if not isinstance(raw, dict):
        raise LocalConfigError("로컬 secret config 최상위 값은 object여야 합니다.")

    environment = _required_string(raw, "environment")
    if environment != "local":
        raise LocalConfigError("로컬 secret config는 environment=local일 때만 사용할 수 있습니다.")

    api = _required_object(raw, "api")
    database = _optional_object(raw, "database")
    auth = _required_object(raw, "auth")

    return LocalSecretConfig(
        environment=environment,
        api=LocalApiConfig(base_url=_required_string(api, "api.base_url", "base_url")),
        database=LocalDatabaseConfig(url=_optional_string(database, "database.url", "url")),
        auth=LocalAuthConfig(
            admin_login_id=_required_string(auth, "auth.admin_login_id", "admin_login_id"),
            current_password=(
                _required_string(auth, "auth.current_password", "current_password")
                if require_current_password
                else _optional_string(auth, "auth.current_password", "current_password") or ""
            ),
            new_password=_required_string(auth, "auth.new_password", "new_password"),
        ),
        source_path=config_path,
    )


def _required_object(data: dict[str, Any], field_name: str) -> dict[str, Any]:
    value = data.get(field_name)
    if not isinstance(value, dict):
        raise LocalConfigError(f"필수 object 값이 없습니다: {field_name}")
    return value


def _optional_object(data: dict[str, Any], field_name: str) -> dict[str, Any]:
    value = data.get(field_name, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise LocalConfigError(f"object 형식이어야 합니다: {field_name}")
    return value


def _required_string(
    data: dict[str, Any],
    display_name: str,
    key: str | None = None,
) -> str:
    actual_key = key or display_name
    value = data.get(actual_key)
    if not isinstance(value, str) or not value.strip():
        raise LocalConfigError(f"필수 문자열 값이 비어 있습니다: {display_name}")
    return value.strip()


def _optional_string(
    data: dict[str, Any],
    display_name: str,
    key: str | None = None,
) -> str | None:
    actual_key = key or display_name
    value = data.get(actual_key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise LocalConfigError(f"문자열 형식이어야 합니다: {display_name}")
    stripped = value.strip()
    return stripped or None
