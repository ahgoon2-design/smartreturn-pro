"""로컬 개발 전용 SUPER_ADMIN 비밀번호 재설정 스크립트."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import Session, sessionmaker

from _local_config import LocalConfigError, LocalSecretConfig, load_local_secret_config


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.core.security import hash_password, validate_password_policy  # noqa: E402
from app.models.auth import Role, User, UserRole  # noqa: E402


LOCAL_DB_HOSTS = {"localhost", "127.0.0.1", "::1"}
BLOCKED_ENV_VALUES = {"production", "prod", "staging", "stage"}
SUPER_ADMIN_ROLE_CODE = "SUPER_ADMIN"


class ResetLocalAdminPasswordError(RuntimeError):
    """로컬 관리자 비밀번호 재설정을 안전하게 진행할 수 없을 때 사용한다."""


@dataclass(frozen=True)
class ResetResult:
    result_code: str
    login_id: str
    must_change_password: bool


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SmartReturn Pro 로컬 전용 관리자 비밀번호 재설정"
    )
    parser.add_argument(
        "--confirm-local-reset",
        action="store_true",
        help="로컬 개발 DB 대상 재설정을 명시적으로 확인한다.",
    )
    parser.add_argument(
        "--secret-file",
        help="로컬 secret config 경로. 생략하면 SMARTRETURN_LOCAL_SECRET_FILE 또는 backend/local.secret.json을 사용한다.",
    )
    parser.add_argument(
        "--require-password-change",
        action="store_true",
        help="재설정 후 must_change_password=true로 둔다. 기본값은 false다.",
    )
    args = parser.parse_args()

    try:
        result = reset_from_local_secret(
            secret_file=args.secret_file,
            confirm_local_reset=args.confirm_local_reset,
            require_password_change=args.require_password_change,
        )
    except (LocalConfigError, ResetLocalAdminPasswordError) as exc:
        print(f"[FAIL] {exc}")
        return 1

    print("[OK] 로컬 관리자 비밀번호 재설정 완료")
    print(f"- login_id: {result.login_id}")
    print(f"- must_change_password: {str(result.must_change_password).lower()}")
    print("- DB host: local 확인 완료")
    print("- 다음 단계: uvicorn 실행 후 scripts\\verify_master_api_local.py를 실행하세요.")
    return 0


def reset_from_local_secret(
    *,
    secret_file: str | Path | None = None,
    confirm_local_reset: bool,
    require_password_change: bool = False,
) -> ResetResult:
    if not confirm_local_reset:
        raise ResetLocalAdminPasswordError("--confirm-local-reset 옵션이 필요합니다.")

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
        result = reset_local_admin_password(
            db,
            login_id=config.auth.admin_login_id,
            new_password=config.auth.new_password,
            must_change_password=require_password_change,
        )
    finally:
        db.close()
        engine.dispose()
    return result


def resolve_database_url(config: LocalSecretConfig) -> str:
    if config.database.url:
        return config.database.url
    return get_settings().database_url


def ensure_runtime_environment_is_local() -> None:
    for name in ("APP_ENV", "ENV", "app_env"):
        value = os.getenv(name)
        if value and value.strip().lower() in BLOCKED_ENV_VALUES:
            raise ResetLocalAdminPasswordError("운영 또는 스테이징 환경에서는 실행할 수 없습니다.")


def ensure_database_url_is_local(database_url: str) -> None:
    if not database_url or not database_url.strip():
        raise ResetLocalAdminPasswordError("DB URL이 비어 있어 실행할 수 없습니다.")

    try:
        parsed = make_url(database_url)
    except ArgumentError as exc:
        raise ResetLocalAdminPasswordError("DB URL 형식을 확인할 수 없어 실행할 수 없습니다.") from exc

    host = (parsed.host or "").strip().lower()
    if host not in LOCAL_DB_HOSTS:
        raise ResetLocalAdminPasswordError("로컬 DB host가 아니므로 실행을 중단합니다.")


def reset_local_admin_password(
    db: Session,
    *,
    login_id: str,
    new_password: str,
    must_change_password: bool = False,
) -> ResetResult:
    login_id = (login_id or "").strip()
    if not login_id:
        db.rollback()
        raise ResetLocalAdminPasswordError("관리자 login_id가 비어 있습니다.")

    password_errors = validate_password_policy(new_password)
    if password_errors:
        db.rollback()
        raise ResetLocalAdminPasswordError("새 비밀번호가 정책을 통과하지 못했습니다.")

    user = db.query(User).filter(User.login_id == login_id).one_or_none()
    if user is None:
        db.rollback()
        raise ResetLocalAdminPasswordError("재설정 대상 사용자를 찾을 수 없습니다.")
    if not user.active_yn:
        db.rollback()
        raise ResetLocalAdminPasswordError("비활성 사용자는 재설정할 수 없습니다.")
    if not user_has_super_admin_role(db, user.id):
        db.rollback()
        raise ResetLocalAdminPasswordError("SUPER_ADMIN 사용자만 재설정할 수 있습니다.")

    user.password_hash = hash_password(new_password)
    user.must_change_password = must_change_password
    if hasattr(user, "updated_at"):
        user.updated_at = datetime.now(UTC)
    db.commit()

    return ResetResult(
        result_code="PASSWORD_RESET",
        login_id=user.login_id,
        must_change_password=user.must_change_password,
    )


def user_has_super_admin_role(db: Session, user_id: int) -> bool:
    return (
        db.query(Role.id)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(
            UserRole.user_id == user_id,
            Role.role_code == SUPER_ADMIN_ROLE_CODE,
            Role.active_yn.is_(True),
        )
        .first()
        is not None
    )


if __name__ == "__main__":
    raise SystemExit(main())
