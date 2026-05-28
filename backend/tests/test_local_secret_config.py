from __future__ import annotations

import json
import shutil
import sys
from uuid import uuid4
from pathlib import Path

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = BACKEND_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from _local_config import LocalConfigError, load_local_secret_config  # noqa: E402


def _test_dir() -> Path:
    path = BACKEND_ROOT / "tmp" / "test_local_secret_config" / uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    return path


def _write_config(data: dict) -> Path:
    config_path = _test_dir() / "local.secret.json"
    config_path.write_text(json.dumps(data), encoding="utf-8")
    return config_path


def _valid_config() -> dict:
    return {
        "environment": "local",
        "api": {"base_url": "http://127.0.0.1:8000"},
        "database": {"url": ""},
        "auth": {
            "admin_login_id": "local_super_admin",
            "current_password": "dummy-current-password",
            "new_password": "dummy-new-password",
        },
    }


def test_local_secret_example_is_valid_json() -> None:
    example_path = BACKEND_ROOT / "local.secret.example.json"

    data = json.loads(example_path.read_text(encoding="utf-8"))

    assert data["environment"] == "local"
    assert data["api"]["base_url"] == "http://127.0.0.1:8000"
    assert data["auth"]["admin_login_id"] == "local_super_admin"
    assert data["auth"]["current_password"] == ""
    assert data["auth"]["new_password"] == ""


def test_load_local_secret_config_reads_valid_config() -> None:
    config_path = _write_config(_valid_config())

    config = load_local_secret_config(config_path)

    assert config.environment == "local"
    assert config.api.base_url == "http://127.0.0.1:8000"
    assert config.database.url is None
    assert config.auth.admin_login_id == "local_super_admin"


def test_load_local_secret_config_rejects_non_local_environment() -> None:
    data = _valid_config()
    data["environment"] = "production"
    config_path = _write_config(data)

    with pytest.raises(LocalConfigError, match="environment=local"):
        load_local_secret_config(config_path)


@pytest.mark.parametrize(
    "field_name",
    ["admin_login_id", "current_password", "new_password"],
)
def test_load_local_secret_config_rejects_empty_auth_values(
    field_name: str,
) -> None:
    data = _valid_config()
    data["auth"][field_name] = ""
    config_path = _write_config(data)

    with pytest.raises(LocalConfigError, match=f"auth.{field_name}"):
        load_local_secret_config(config_path)


def test_error_message_does_not_include_password_value() -> None:
    secret_value = "dummy-current-password"
    data = _valid_config()
    data["environment"] = "production"
    config_path = _write_config(data)

    with pytest.raises(LocalConfigError) as exc_info:
        load_local_secret_config(config_path)

    assert secret_value not in str(exc_info.value)


def test_explicit_config_path_does_not_require_default_local_secret_file() -> None:
    example_path = BACKEND_ROOT / "local.secret.example.json"
    config_path = _write_config(_valid_config())

    assert example_path.exists()
    config = load_local_secret_config(config_path)
    assert config.auth.admin_login_id == "local_super_admin"


def teardown_module() -> None:
    shutil.rmtree(BACKEND_ROOT / "tmp" / "test_local_secret_config", ignore_errors=True)
