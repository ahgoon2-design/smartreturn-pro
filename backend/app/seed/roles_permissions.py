from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.auth import Permission, Role, RolePermission


ROLE_SEED_DATA = [
    {
        "role_code": "SUPER_ADMIN",
        "role_name": "최고 관리자",
        "role_type": "INTERNAL",
        "active_yn": True,
    },
    {
        "role_code": "INTERNAL_ADMIN",
        "role_name": "내부 관리자",
        "role_type": "INTERNAL",
        "active_yn": True,
    },
    {
        "role_code": "INTERNAL_WORKER",
        "role_name": "내부 작업자",
        "role_type": "INTERNAL",
        "active_yn": True,
    },
    {
        "role_code": "CLIENT_ADMIN",
        "role_name": "고객사 관리자",
        "role_type": "CLIENT",
        "active_yn": True,
    },
    {
        "role_code": "CLIENT_USER",
        "role_name": "고객사 사용자",
        "role_type": "CLIENT",
        "active_yn": True,
    },
    {
        "role_code": "READ_ONLY",
        "role_name": "읽기 전용",
        "role_type": "CLIENT",
        "active_yn": True,
    },
]


PERMISSION_SEED_DATA = [
    {
        "permission_code": "SYSTEM_ADMIN",
        "permission_name": "시스템 관리",
        "description": "시스템 위험 설정과 전역 운영 설정 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "USER_MANAGE",
        "permission_name": "사용자 관리",
        "description": "사용자 생성, 사용중지, 비밀번호 초기화 후보 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "ROLE_MANAGE",
        "permission_name": "역할 관리",
        "description": "role과 permission 매핑을 관리하는 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "MASTER_VIEW",
        "permission_name": "기준정보 조회",
        "description": "고객사, 창고, 상품, 공통코드 기준정보 조회 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "MASTER_MANAGE",
        "permission_name": "기준정보 관리",
        "description": "기준정보 생성, 수정, 사용중지 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "CLIENT_MANAGE",
        "permission_name": "고객사 관리",
        "description": "고객사 기준정보 관리 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "WAREHOUSE_MANAGE",
        "permission_name": "창고 관리",
        "description": "창고와 고객사 사용창고 설정 관리 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "PRODUCT_MANAGE",
        "permission_name": "상품 관리",
        "description": "상품과 추가 바코드 관리 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "COMMON_CODE_MANAGE",
        "permission_name": "공통코드 관리",
        "description": "공통코드 그룹과 코드값 관리 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "IMPORT_VIEW",
        "permission_name": "업로드 조회",
        "description": "import job, 업로드 이력, 검증 결과 조회 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "IMPORT_MANAGE",
        "permission_name": "업로드 관리",
        "description": "업로드 preview, 검증, 저장 확정 후보 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "RETURN_VIEW",
        "permission_name": "반품 조회",
        "description": "반품 자료와 처리 결과 조회 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "RETURN_PREPARE",
        "permission_name": "반품자료 준비",
        "description": "CJ/택배 반품예정 자료 등록과 저장 확정 후보 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "RETURN_PROCESS",
        "permission_name": "반품처리",
        "description": "실제 도착 반품 스캔과 작업 시작 후보 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "RETURN_JUDGE",
        "permission_name": "반품 판정",
        "description": "반품 상품, 수량, 판정 저장 후보 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "RETURN_CLOSE",
        "permission_name": "반품 마감",
        "description": "판정 완료 결과 대조와 마감확정 후보 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "RETURN_OUTBOUND",
        "permission_name": "반품 반출",
        "description": "외부반출 묶음 생성, 스캔 대조, 반출확정 후보 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "RETURN_TRACE",
        "permission_name": "반품 통합추적",
        "description": "반품 전체 흐름 읽기 전용 추적 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "INBOUND_VIEW",
        "permission_name": "입고 조회",
        "description": "입고 자료와 입고 결과 조회 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "INBOUND_PROCESS",
        "permission_name": "입고 처리",
        "description": "입고검수 작업 후보 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "INBOUND_CONFIRM",
        "permission_name": "입고 확정",
        "description": "입고 확정 후보 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "OUTBOUND_VIEW",
        "permission_name": "출고 조회",
        "description": "출고 자료와 출고 결과 조회 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "OUTBOUND_PROCESS",
        "permission_name": "출고 처리",
        "description": "출고검수 작업 후보 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "OUTBOUND_CONFIRM",
        "permission_name": "출고 확정",
        "description": "출고 확정 후보 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "INVENTORY_VIEW",
        "permission_name": "재고 조회",
        "description": "현재고와 기본 재고 현황 조회 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "INVENTORY_EVENT_VIEW",
        "permission_name": "재고 이벤트 조회",
        "description": "inventory_events 이력 조회 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "INVENTORY_ADJUST",
        "permission_name": "재고 조정",
        "description": "수동 재고 조정 후보 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "SETTLEMENT_VIEW",
        "permission_name": "정산 조회",
        "description": "정산 결과 조회 후보 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "SETTLEMENT_MANAGE",
        "permission_name": "정산 관리",
        "description": "정산 생성, 마감, 조정 후보 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "LOCAL_AGENT_VIEW",
        "permission_name": "Local Agent 조회",
        "description": "장치 연결상태와 로그 조회 후보 권한이다.",
        "active_yn": True,
    },
    {
        "permission_code": "LOCAL_AGENT_MANAGE",
        "permission_name": "Local Agent 관리",
        "description": "장치 설정과 등록 관리 후보 권한이다.",
        "active_yn": True,
    },
]


INTERNAL_ADMIN_PERMISSIONS = [
    "USER_MANAGE",
    "MASTER_VIEW",
    "MASTER_MANAGE",
    "CLIENT_MANAGE",
    "WAREHOUSE_MANAGE",
    "PRODUCT_MANAGE",
    "COMMON_CODE_MANAGE",
    "IMPORT_VIEW",
    "IMPORT_MANAGE",
    "RETURN_VIEW",
    "RETURN_PREPARE",
    "RETURN_PROCESS",
    "RETURN_JUDGE",
    "RETURN_CLOSE",
    "RETURN_OUTBOUND",
    "RETURN_TRACE",
    "INBOUND_VIEW",
    "INBOUND_PROCESS",
    "INBOUND_CONFIRM",
    "OUTBOUND_VIEW",
    "OUTBOUND_PROCESS",
    "OUTBOUND_CONFIRM",
    "INVENTORY_VIEW",
    "INVENTORY_EVENT_VIEW",
    "LOCAL_AGENT_VIEW",
]

INTERNAL_WORKER_PERMISSIONS = [
    "MASTER_VIEW",
    "RETURN_VIEW",
    "RETURN_PROCESS",
    "RETURN_JUDGE",
    "RETURN_CLOSE",
    "RETURN_OUTBOUND",
    "INBOUND_VIEW",
    "INBOUND_PROCESS",
    "OUTBOUND_VIEW",
    "OUTBOUND_PROCESS",
    "INVENTORY_VIEW",
    "LOCAL_AGENT_VIEW",
]

CLIENT_ADMIN_PERMISSIONS = [
    "MASTER_VIEW",
    "IMPORT_VIEW",
    "RETURN_VIEW",
    "RETURN_TRACE",
    "INBOUND_VIEW",
    "OUTBOUND_VIEW",
    "INVENTORY_VIEW",
    "SETTLEMENT_VIEW",
]

CLIENT_USER_PERMISSIONS = [
    "RETURN_VIEW",
    "RETURN_TRACE",
    "OUTBOUND_VIEW",
    "INVENTORY_VIEW",
    "SETTLEMENT_VIEW",
]

READ_ONLY_PERMISSIONS = [
    "RETURN_VIEW",
    "RETURN_TRACE",
    "OUTBOUND_VIEW",
    "INVENTORY_VIEW",
    "SETTLEMENT_VIEW",
]


def get_role_seed_data() -> list[dict[str, object]]:
    return [role.copy() for role in ROLE_SEED_DATA]


def get_permission_seed_data() -> list[dict[str, object]]:
    return [permission.copy() for permission in PERMISSION_SEED_DATA]


def get_role_permission_seed_data() -> dict[str, list[str]]:
    all_permissions = [permission["permission_code"] for permission in PERMISSION_SEED_DATA]
    return {
        "SUPER_ADMIN": list(all_permissions),
        "INTERNAL_ADMIN": list(INTERNAL_ADMIN_PERMISSIONS),
        "INTERNAL_WORKER": list(INTERNAL_WORKER_PERMISSIONS),
        "CLIENT_ADMIN": list(CLIENT_ADMIN_PERMISSIONS),
        "CLIENT_USER": list(CLIENT_USER_PERMISSIONS),
        "READ_ONLY": list(READ_ONLY_PERMISSIONS),
    }


def _update_if_changed(model: object, values: dict[str, object], fields: list[str]) -> bool:
    changed = False
    for field in fields:
        if getattr(model, field) != values[field]:
            setattr(model, field, values[field])
            changed = True
    return changed


def seed_roles_permissions(db: Session) -> dict[str, object]:
    result: dict[str, object] = {
        "roles_created": 0,
        "roles_updated": 0,
        "permissions_created": 0,
        "permissions_updated": 0,
        "role_permissions_created": 0,
        "skipped": 0,
        "warnings": [],
    }

    try:
        role_by_code: dict[str, Role] = {}
        for role_data in get_role_seed_data():
            role_code = str(role_data["role_code"])
            role = db.query(Role).filter(Role.role_code == role_code).one_or_none()
            if role is None:
                role = Role(**role_data)
                db.add(role)
                result["roles_created"] += 1
            elif _update_if_changed(role, role_data, ["role_name", "role_type", "active_yn"]):
                result["roles_updated"] += 1
            else:
                result["skipped"] += 1
            role_by_code[role_code] = role

        permission_by_code: dict[str, Permission] = {}
        for permission_data in get_permission_seed_data():
            permission_code = str(permission_data["permission_code"])
            permission = db.query(Permission).filter(Permission.permission_code == permission_code).one_or_none()
            if permission is None:
                permission = Permission(**permission_data)
                db.add(permission)
                result["permissions_created"] += 1
            elif _update_if_changed(
                permission,
                permission_data,
                ["permission_name", "description", "active_yn"],
            ):
                result["permissions_updated"] += 1
            else:
                result["skipped"] += 1
            permission_by_code[permission_code] = permission

        db.flush()

        warnings: list[str] = result["warnings"]  # type: ignore[assignment]
        for role_code, permission_codes in get_role_permission_seed_data().items():
            role = role_by_code.get(role_code)
            if role is None:
                warnings.append(f"{role_code} role을 찾을 수 없어 매핑을 건너뜁니다.")
                continue

            for permission_code in permission_codes:
                permission = permission_by_code.get(permission_code)
                if permission is None:
                    warnings.append(f"{permission_code} permission을 찾을 수 없어 매핑을 건너뜁니다.")
                    continue

                exists = (
                    db.query(RolePermission)
                    .filter(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == permission.id,
                    )
                    .one_or_none()
                )
                if exists is None:
                    db.add(RolePermission(role_id=role.id, permission_id=permission.id))
                    result["role_permissions_created"] += 1
                else:
                    result["skipped"] += 1

        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
