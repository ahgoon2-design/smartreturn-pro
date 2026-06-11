"""로컬 개발용 로그인 테스트 계정 seed 스크립트.

스마트리턴프로 로그인/권한/고객 포털 진입 테스트를 위해 내부(슈퍼관리자),
대리점(AGENCY_ADMIN), 고객사(CLIENT_ADMIN) 테스트 계정을 로컬 개발 DB에 생성/갱신한다.

- 실제 운영 계정 생성이 아니라 로컬 개발 테스트 전용이다.
- 여러 번 실행해도 중복이 생기지 않도록 idempotent하게 동작한다(있으면 갱신, 없으면 생성).
- 비밀번호는 요청된 공통 테스트 비밀번호로 통일한다(SEED_TEST_PASSWORD로 override 가능).
- 기존 password 해시 유틸을 재사용한다. 회원가입/비밀번호 변경 정책은 변경하지 않는다.
- 운영 DB로 보이는 환경에서는 기존 로컬 안전가드로 실행을 막는다.

선행 조건:
    python scripts/seed_p0.py   # role/permission seed (SUPER_ADMIN/AGENCY_ADMIN/CLIENT_ADMIN 등)

사용 예:
    cd C:\\smartreturn-pro\\backend
    & .venv\\Scripts\\python.exe scripts\\seed_local_login_test_accounts.py --confirm-local-fixture
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from _local_config import LocalConfigError, load_local_secret_config
from reset_local_admin_password import (
    ensure_database_url_is_local,
    ensure_runtime_environment_is_local,
    resolve_database_url,
)


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.security import hash_password_unchecked  # noqa: E402
from app.models.auth import Role, User, UserRole  # noqa: E402
from app.models.master import Agency, Client  # noqa: E402


# 요청된 공통 테스트 비밀번호. 운영값이 아니며 로컬 테스트 전용이다.
DEFAULT_TEST_PASSWORD = "0402"

AGENCY_CODE = "517593"
AGENCY_NAME = "CJ 대리점 517593"

# (client_code, client_name)
TEST_CLIENTS = [
    ("ESPMARKETING", "ESPMARKETING"),
    ("GATEVISION", "GATEVISION"),
    ("PEOPLEGLOW", "PEOPLEGLOW"),
]


class SeedLoginAccountsError(RuntimeError):
    """로컬 로그인 테스트 계정을 안전하게 준비할 수 없을 때 사용한다."""


@dataclass
class SeedSummary:
    agency_action: str = ""
    client_actions: dict[str, str] = field(default_factory=dict)
    user_actions: list[tuple[str, str, str]] = field(default_factory=list)  # (login_id, role, action)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SmartReturn Pro 로컬 로그인 테스트 계정을 생성/갱신합니다."
    )
    parser.add_argument(
        "--confirm-local-fixture",
        action="store_true",
        help="로컬 개발 DB에 테스트 계정을 만든다는 점을 명시적으로 확인한다.",
    )
    parser.add_argument("--secret-file", help="로컬 secret config 경로(생략 시 기본 경로).")
    args = parser.parse_args()

    print("[로컬 테스트 계정 seed] 운영 계정 생성이 아니라 로컬 개발 로그인 테스트용입니다.")

    # 비밀번호는 환경변수로 override 가능. 셸 인자로 받지 않아 히스토리 노출을 줄인다.
    test_password = os.getenv("SEED_TEST_PASSWORD", DEFAULT_TEST_PASSWORD)

    try:
        summary = seed_from_local_secret(
            secret_file=args.secret_file,
            confirm_local_fixture=args.confirm_local_fixture,
            test_password=test_password,
        )
    except (LocalConfigError, SeedLoginAccountsError) as exc:
        print(f"[FAIL] {exc}")
        return 1

    print("[OK] 로컬 로그인 테스트 계정 준비 완료")
    print(f"- agency({AGENCY_CODE}): {summary.agency_action}")
    for code, action in summary.client_actions.items():
        print(f"- client({code}): {action}")
    for login_id, role_code, action in summary.user_actions:
        print(f"- user {login_id} [{role_code}]: {action}")
    print("- 비밀번호: 요청하신 공통 테스트 비밀번호로 설정(must_change_password=false)")
    print("- 다음 단계: uvicorn 실행 후 각 계정으로 로그인하여 내부/포털 진입 확인")
    return 0


def seed_from_local_secret(
    *,
    secret_file: str | Path | None,
    confirm_local_fixture: bool,
    test_password: str,
) -> SeedSummary:
    if not confirm_local_fixture:
        raise SeedLoginAccountsError("--confirm-local-fixture 옵션이 필요합니다.")

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
        summary = seed_login_test_accounts(db, test_password=test_password)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        engine.dispose()
    return summary


def seed_login_test_accounts(db: Session, *, test_password: str) -> SeedSummary:
    summary = SeedSummary()
    password_hash = hash_password_unchecked(test_password)

    # 1) 대리점(agency) 기준정보
    agency, summary.agency_action = _upsert_agency(db, AGENCY_CODE, AGENCY_NAME)

    # 2) 고객사(client) 기준정보 (대리점 하위)
    clients: dict[str, Client] = {}
    for code, name in TEST_CLIENTS:
        client, action = _upsert_client(db, code=code, name=name, agency_id=agency.id)
        clients[code] = client
        summary.client_actions[code] = action

    db.flush()

    # 3) 사용자 계정
    # 3-1) 개발 슈퍼관리자(내부) - agency/client 미지정
    _, action = _upsert_user(
        db,
        login_id="ahgoon",
        user_name="허곤(개발 슈퍼관리자)",
        role_code="SUPER_ADMIN",
        password_hash=password_hash,
        agency_id=None,
        client_id=None,
    )
    summary.user_actions.append(("ahgoon", "SUPER_ADMIN", action))

    # 3-2) 대리점 관리자
    _, action = _upsert_user(
        db,
        login_id=AGENCY_CODE,
        user_name="CJ 대리점 517593 관리자",
        role_code="AGENCY_ADMIN",
        password_hash=password_hash,
        agency_id=agency.id,
        client_id=None,
    )
    summary.user_actions.append((AGENCY_CODE, "AGENCY_ADMIN", action))

    # 3-3) 고객사 관리자 (고객 사용자, 로그인 후 /portal/dashboard 진입)
    for code, _name in TEST_CLIENTS:
        client = clients[code]
        _, action = _upsert_user(
            db,
            login_id=code,
            user_name=f"{code} 관리자",
            role_code="CLIENT_ADMIN",
            password_hash=password_hash,
            agency_id=agency.id,
            client_id=client.id,
        )
        summary.user_actions.append((code, "CLIENT_ADMIN", action))

    return summary


def _upsert_agency(db: Session, code: str, name: str) -> tuple[Agency, str]:
    agency = db.query(Agency).filter(Agency.agency_code == code).one_or_none()
    if agency is None:
        agency = Agency(agency_code=code, agency_name=name, active_yn=True, remarks="로컬 테스트 대리점")
        db.add(agency)
        db.flush()
        return agency, "created"
    if not agency.active_yn:
        agency.active_yn = True
        return agency, "reactivated"
    return agency, "reused"


def _upsert_client(db: Session, *, code: str, name: str, agency_id: int) -> tuple[Client, str]:
    client = db.query(Client).filter(Client.client_code == code).one_or_none()
    if client is None:
        client = Client(
            client_code=code,
            client_name=name,
            agency_id=agency_id,
            active_yn=True,
            use_returns=True,
            remarks="로컬 테스트 고객사",
        )
        db.add(client)
        db.flush()
        return client, "created"

    # 대리점 연결과 활성 상태만 테스트 가능하도록 보정한다.
    changed = False
    if client.agency_id != agency_id:
        client.agency_id = agency_id
        changed = True
    if not client.active_yn:
        client.active_yn = True
        changed = True
    return client, ("updated" if changed else "reused")


def _upsert_user(
    db: Session,
    *,
    login_id: str,
    user_name: str,
    role_code: str,
    password_hash: str,
    agency_id: int | None,
    client_id: int | None,
) -> tuple[User, str]:
    role = db.query(Role).filter(Role.role_code == role_code).one_or_none()
    if role is None:
        raise SeedLoginAccountsError(
            f"{role_code} role이 없습니다. 먼저 `python scripts/seed_p0.py`로 role/permission seed를 실행하세요."
        )

    user = db.query(User).filter(User.login_id == login_id).one_or_none()
    if user is None:
        user = User(
            login_id=login_id,
            user_name=user_name,
            password_hash=password_hash,
            agency_id=agency_id,
            client_id=client_id,
            must_change_password=False,
            active_yn=True,
            remarks="로컬 로그인 테스트 계정",
        )
        db.add(user)
        db.flush()
        action = "created"
    else:
        # 기존 계정은 삭제하지 않고 비밀번호/상태/연결만 테스트 가능하게 갱신한다.
        user.user_name = user_name
        user.password_hash = password_hash
        user.must_change_password = False
        user.active_yn = True
        # agency/client는 지정된 경우(대리점/고객 계정)에만 갱신해 내부 계정 연결을 건드리지 않는다.
        if agency_id is not None:
            user.agency_id = agency_id
        if client_id is not None:
            user.client_id = client_id
        action = "updated"

    _ensure_single_role(db, user, role)
    return user, action


def _ensure_single_role(db: Session, user: User, role: Role) -> None:
    """사용자의 role을 지정 role 하나로 맞춘다(테스트 시 역할 혼선 방지)."""
    existing = db.query(UserRole).filter(UserRole.user_id == user.id).all()
    has_target = False
    for link in existing:
        if link.role_id == role.id:
            has_target = True
        else:
            db.delete(link)
    if not has_target:
        db.add(UserRole(user_id=user.id, role_id=role.id))


if __name__ == "__main__":
    raise SystemExit(main())
