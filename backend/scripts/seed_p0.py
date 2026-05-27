from __future__ import annotations

import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.seed.roles_permissions import seed_roles_permissions  # noqa: E402


def main() -> int:
    db = SessionLocal()
    try:
        result = seed_roles_permissions(db)
    except Exception as exc:
        print(f"P0 role/permission seed 실행 실패: {exc}")
        return 1
    finally:
        db.close()

    print("P0 role/permission seed 실행 완료")
    print(f"- role 생성: {result['roles_created']}")
    print(f"- role 갱신: {result['roles_updated']}")
    print(f"- permission 생성: {result['permissions_created']}")
    print(f"- permission 갱신: {result['permissions_updated']}")
    print(f"- role_permission 생성: {result['role_permissions_created']}")
    print(f"- 건너뜀: {result['skipped']}")

    warnings = result["warnings"]
    if warnings:
        print("- 경고:")
        for warning in warnings:
            print(f"  - {warning}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
