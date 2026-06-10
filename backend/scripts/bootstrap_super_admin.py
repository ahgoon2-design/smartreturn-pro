"""초기 SUPER_ADMIN 계정을 생성하는 콘솔 스크립트."""

from __future__ import annotations

import getpass
import os
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.seed.super_admin import bootstrap_super_admin  # noqa: E402


def _read_value(env_name: str, prompt: str, default: str | None = None) -> str:
    value = os.getenv(env_name)
    if value:
        return value

    entered = input(prompt).strip()
    if entered:
        return entered
    return default or ""


def _read_password() -> str:
    value = os.getenv("BOOTSTRAP_ADMIN_PASSWORD")
    if value:
        return value
    return getpass.getpass("초기 비밀번호: ")


def main() -> int:
    print("먼저 `python scripts/seed_p0.py`로 role/permission seed를 실행해야 합니다.")

    login_id = _read_value("BOOTSTRAP_ADMIN_LOGIN_ID", "관리자 login_id: ")
    user_name = _read_value(
        "BOOTSTRAP_ADMIN_NAME",
        "관리자 이름(비우면 최고 관리자): ",
        "최고 관리자",
    )
    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL") or None
    plain_password = _read_password()

    db = SessionLocal()
    try:
        result = bootstrap_super_admin(
            db=db,
            login_id=login_id,
            user_name=user_name,
            plain_password=plain_password,
            email=email,
        )
    finally:
        db.close()

    print(f"결과 코드: {result.get('result_code')}")
    print(f"메시지: {result.get('message')}")
    if result.get("result_code") == "ROLE_NOT_SEEDED":
        print("조치: `python scripts/seed_p0.py`를 먼저 실행하세요.")
    if result.get("login_id"):
        print(f"login_id: {result.get('login_id')}")
    if "must_change_password" in result:
        value = "true" if result.get("must_change_password") else "false"
        print(f"must_change_password: {value}")

    return 0 if result.get("result_code") in {"CREATED", "SUPER_ADMIN_EXISTS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
