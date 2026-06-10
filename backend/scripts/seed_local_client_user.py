"""로컬 개발/테스트용 고객(client) 사용자 계정을 생성하는 콘솔 스크립트.

내부 운영자와 분리된 고객 포털 로그인 흐름을 브라우저에서 검증하기 위한 개발용 계정을 만든다.
운영 환경에서는 사용하지 않으며, 로컬 DB에서만 동작하도록 안전가드를 적용한다.

사용 예:
    SEED_CLIENT_USER_PASSWORD=client-test-1234 \
    python scripts/seed_local_client_user.py --confirm-local-fixture

선행 조건:
    1) python scripts/seed_p0.py            # role/permission seed (CLIENT_ADMIN 등)
    2) (자동) LOCAL_TEST_CLIENT 기준정보 fixture 준비
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from _local_config import LocalConfigError, load_local_secret_config
from reset_local_admin_password import (
    ensure_database_url_is_local,
    ensure_runtime_environment_is_local,
    resolve_database_url,
)
from seed_local_master_fixture import LOCAL_FIXTURE_CLIENT_CODE, seed_local_master_fixture


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.security import hash_password  # noqa: E402
from app.models.auth import Role, User, UserRole  # noqa: E402
from app.models.master import Client  # noqa: E402


DEFAULT_LOGIN_ID = "client_test"
DEFAULT_USER_NAME = "로컬검증 고객사용자"
DEFAULT_ROLE_CODE = "CLIENT_ADMIN"
ALLOWED_ROLE_CODES = {"CLIENT_ADMIN", "CLIENT_USER", "READ_ONLY"}


class SeedLocalClientUserError(RuntimeError):
    """로컬 고객 테스트 계정을 안전하게 준비할 수 없을 때 사용한다."""


@dataclass(frozen=True)
class SeedLocalClientUserResult:
    result_code: str
    action: str
    login_id: str
    user_id: int
    client_id: int
    role_code: str
    must_change_password: bool


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SmartReturn Pro 로컬 검증용 고객(client) 사용자 계정을 준비합니다."
    )
    parser.add_argument(
        "--confirm-local-fixture",
        action="store_true",
        help="로컬 개발 DB에 계정을 만든다는 점을 명시적으로 확인한다.",
    )
    parser.add_argument("--secret-file", help="로컬 secret config 경로(생략 시 기본 경로).")
    parser.add_argument("--login-id", default=DEFAULT_LOGIN_ID, help=f"고객 사용자 login_id (기본: {DEFAULT_LOGIN_ID}).")
    parser.add_argument("--user-name", default=DEFAULT_USER_NAME, help="고객 사용자 표시 이름.")
    parser.add_argument(
        "--role-code",
        default=DEFAULT_ROLE_CODE,
        choices=sorted(ALLOWED_ROLE_CODES),
        help=f"부여할 고객 role (기본: {DEFAULT_ROLE_CODE}).",
    )
    parser.add_argument(
        "--reactivate-existing",
        action="store_true",
        help="LOCAL_TEST_CLIENT가 inactive면 active로 보정한다.",
    )
    args = parser.parse_args()

    # 비밀번호는 인자가 아니라 환경변수로만 받아 셸 히스토리/출력 노출을 피한다.
    plain_password = os.getenv("SEED_CLIENT_USER_PASSWORD", "")

    try:
        result = seed_from_local_secret(
            secret_file=args.secret_file,
            confirm_local_fixture=args.confirm_local_fixture,
            login_id=args.login_id,
            user_name=args.user_name,
            role_code=args.role_code,
            plain_password=plain_password,
            reactivate_existing=args.reactivate_existing,
        )
    except (LocalConfigError, SeedLocalClientUserError) as exc:
        print(f"[FAIL] {exc}")
        return 1

    print("[OK] 로컬 고객 테스트 계정 준비 완료")
    print(f"- action: {result.action}")
    print(f"- login_id: {result.login_id}")
    print(f"- user_id: {result.user_id}")
    print(f"- client_id: {result.client_id}")
    print(f"- role_code: {result.role_code}")
    print(f"- must_change_password: {str(result.must_change_password).lower()}")
    print("- 비밀번호: SEED_CLIENT_USER_PASSWORD 환경변수 값(보안상 출력하지 않음)")
    print("- 다음 단계: uvicorn 실행 후 고객 계정으로 로그인하여 /portal/dashboard 진입 확인")
    return 0


def seed_from_local_secret(
    *,
    secret_file: str | Path | None,
    confirm_local_fixture: bool,
    login_id: str,
    user_name: str,
    role_code: str,
    plain_password: str,
    reactivate_existing: bool,
) -> SeedLocalClientUserResult:
    if not confirm_local_fixture:
        raise SeedLocalClientUserError("--confirm-local-fixture 옵션이 필요합니다.")
    if not plain_password:
        raise SeedLocalClientUserError(
            "SEED_CLIENT_USER_PASSWORD 환경변수로 개발용 비밀번호(8자 이상)를 제공해야 합니다."
        )

    config = load_local_secret_config(secret_file, require_current_password=False)
    ensure_runtime_environment_is_local()
    database_url = resolve_database_url(config)
    ensure_database_url_is_local(database_url)

    engine = create_engine(database_url, pool_pre_ping=True, future=True)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=Session,
    )
    db = session_factory()
    try:
        # 고객 사용자가 묶일 active client 기준정보를 보장한다.
        seed_local_master_fixture(db, reactivate_existing=reactivate_existing)
        result = seed_local_client_user(
            db,
            login_id=login_id,
            user_name=user_name,
            role_code=role_code,
            plain_password=plain_password,
        )
    finally:
        db.close()
        engine.dispose()
    return result


def seed_local_client_user(
    db: Session,
    *,
    login_id: str,
    user_name: str,
    role_code: str,
    plain_password: str,
) -> SeedLocalClientUserResult:
    login_id = (login_id or "").strip()
    user_name = (user_name or "").strip()
    if not login_id or not user_name:
        db.rollback()
        raise SeedLocalClientUserError("login_id와 user_name은 필수입니다.")
    if role_code not in ALLOWED_ROLE_CODES:
        db.rollback()
        raise SeedLocalClientUserError(f"허용되지 않은 role_code입니다: {role_code}")
    if plain_password.strip() == login_id:
        db.rollback()
        raise SeedLocalClientUserError("login_id와 동일한 비밀번호는 사용할 수 없습니다.")

    role = db.query(Role).filter(Role.role_code == role_code).one_or_none()
    if role is None:
        db.rollback()
        raise SeedLocalClientUserError(
            f"{role_code} role이 없습니다. 먼저 `python scripts/seed_p0.py`를 실행하세요."
        )

    client = db.query(Client).filter(Client.client_code == LOCAL_FIXTURE_CLIENT_CODE).one_or_none()
    if client is None:
        db.rollback()
        raise SeedLocalClientUserError("LOCAL_TEST_CLIENT 기준정보를 찾을 수 없습니다.")

    existing = db.query(User).filter(User.login_id == login_id).one_or_none()
    if existing is not None:
        db.rollback()
        return SeedLocalClientUserResult(
            result_code="CLIENT_USER_EXISTS",
            action="reused",
            login_id=existing.login_id,
            user_id=existing.id,
            client_id=existing.client_id if existing.client_id is not None else client.id,
            role_code=role_code,
            must_change_password=bool(existing.must_change_password),
        )

    try:
        user = User(
            login_id=login_id,
            user_name=user_name,
            # client_id가 있는 사용자는 clients.agency_id 기준으로 agency_id를 확정한다.
            agency_id=client.agency_id,
            client_id=client.id,
            password_hash=hash_password(plain_password),
            must_change_password=True,
            active_yn=True,
            remarks="로컬 개발 검증용 고객 테스트 계정",
        )
        db.add(user)
        db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id))
        db.commit()
    except Exception as exc:  # noqa: BLE001 - 로컬 스크립트 안전 종료
        db.rollback()
        raise SeedLocalClientUserError("고객 테스트 계정 생성 중 오류가 발생했습니다.") from exc

    return SeedLocalClientUserResult(
        result_code="CLIENT_USER_CREATED",
        action="created",
        login_id=login_id,
        user_id=user.id,
        client_id=client.id,
        role_code=role_code,
        must_change_password=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
