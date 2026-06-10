"""로컬 개발 검증용 기준정보 fixture 생성 스크립트."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
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

from app.models.master import Client  # noqa: E402


LOCAL_FIXTURE_CLIENT_CODE = "LOCAL_TEST_CLIENT"
LOCAL_FIXTURE_CLIENT_NAME = "로컬검증고객사"


class SeedLocalMasterFixtureError(RuntimeError):
    """로컬 기준정보 fixture를 안전하게 준비할 수 없을 때 사용한다."""


@dataclass(frozen=True)
class SeedLocalMasterFixtureResult:
    result_code: str
    action: str
    client_id: int
    client_code: str
    active_yn: bool


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SmartReturn Pro 로컬 검증용 active client fixture를 준비합니다."
    )
    parser.add_argument(
        "--confirm-local-fixture",
        action="store_true",
        help="로컬 개발 DB에 fixture를 준비한다는 점을 명시적으로 확인한다.",
    )
    parser.add_argument(
        "--secret-file",
        help="로컬 secret config 경로. 생략하면 SMARTRETURN_LOCAL_SECRET_FILE 또는 backend/local.secret.json을 사용한다.",
    )
    parser.add_argument(
        "--reactivate-existing",
        action="store_true",
        help="기존 LOCAL_TEST_CLIENT가 inactive일 때 active_yn=true로 보정한다.",
    )
    args = parser.parse_args()

    try:
        result = seed_from_local_secret(
            secret_file=args.secret_file,
            confirm_local_fixture=args.confirm_local_fixture,
            reactivate_existing=args.reactivate_existing,
        )
    except (LocalConfigError, SeedLocalMasterFixtureError) as exc:
        print(f"[FAIL] {exc}")
        return 1

    print("[OK] 로컬 기준정보 fixture 준비 완료")
    print(f"- action: {result.action}")
    print(f"- client_code: {result.client_code}")
    print(f"- client_id: {result.client_id}")
    print(f"- active_yn: {str(result.active_yn).lower()}")
    print("- DB host: local 확인 완료")
    print("- 다음 단계: uvicorn 실행 후 product/product_barcodes 관리 API 수동 검증")
    return 0


def seed_from_local_secret(
    *,
    secret_file: str | Path | None = None,
    confirm_local_fixture: bool,
    reactivate_existing: bool = False,
) -> SeedLocalMasterFixtureResult:
    if not confirm_local_fixture:
        raise SeedLocalMasterFixtureError("--confirm-local-fixture 옵션이 필요합니다.")

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
        result = seed_local_master_fixture(db, reactivate_existing=reactivate_existing)
    finally:
        db.close()
        engine.dispose()
    return result


def seed_local_master_fixture(
    db: Session,
    *,
    reactivate_existing: bool = False,
) -> SeedLocalMasterFixtureResult:
    client = db.query(Client).filter(Client.client_code == LOCAL_FIXTURE_CLIENT_CODE).one_or_none()
    if client is None:
        client = Client(
            client_code=LOCAL_FIXTURE_CLIENT_CODE,
            client_name=LOCAL_FIXTURE_CLIENT_NAME,
            active_yn=True,
            remarks="로컬 개발 검증용 fixture",
        )
        db.add(client)
        db.commit()
        return SeedLocalMasterFixtureResult(
            result_code="LOCAL_MASTER_FIXTURE_CREATED",
            action="created",
            client_id=client.id,
            client_code=client.client_code,
            active_yn=client.active_yn,
        )

    if client.active_yn:
        return SeedLocalMasterFixtureResult(
            result_code="LOCAL_MASTER_FIXTURE_REUSED",
            action="reused",
            client_id=client.id,
            client_code=client.client_code,
            active_yn=client.active_yn,
        )

    if not reactivate_existing:
        db.rollback()
        raise SeedLocalMasterFixtureError(
            "LOCAL_TEST_CLIENT가 inactive 상태입니다. 재활성화하려면 --reactivate-existing 옵션이 필요합니다."
        )

    client.active_yn = True
    if hasattr(client, "updated_at"):
        client.updated_at = datetime.now(UTC)
    db.commit()
    return SeedLocalMasterFixtureResult(
        result_code="LOCAL_MASTER_FIXTURE_REACTIVATED",
        action="reactivated",
        client_id=client.id,
        client_code=client.client_code,
        active_yn=client.active_yn,
    )


if __name__ == "__main__":
    raise SystemExit(main())
