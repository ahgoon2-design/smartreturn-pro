"""초기 SUPER_ADMIN 사용자 bootstrap 로직."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import hash_password, validate_password_policy
from app.models.auth import Role, User, UserRole


SUPER_ADMIN_ROLE_CODE = "SUPER_ADMIN"


def _result(result_code: str, message: str, **extra: object) -> dict:
    safe_result = {
        "result_code": result_code,
        "message": message,
    }
    safe_result.update(extra)
    return safe_result


def bootstrap_super_admin(
    db: Session,
    login_id: str,
    user_name: str,
    plain_password: str,
    email: str | None = None,
) -> dict:
    """SUPER_ADMIN 사용자 1명을 안전하게 생성한다."""

    login_id = (login_id or "").strip()
    user_name = (user_name or "").strip()
    email = (email or "").strip() or None

    if not login_id or not user_name:
        db.rollback()
        return _result("INVALID_INPUT", "login_id와 사용자 이름은 필수입니다.")

    super_admin_role = (
        db.query(Role).filter(Role.role_code == SUPER_ADMIN_ROLE_CODE).one_or_none()
    )
    if super_admin_role is None:
        db.rollback()
        return _result(
            "ROLE_NOT_SEEDED",
            "SUPER_ADMIN role이 없습니다. 먼저 role/permission seed를 실행해야 합니다.",
        )

    existing_super_admin = (
        db.query(User)
        .join(UserRole, User.id == UserRole.user_id)
        .filter(UserRole.role_id == super_admin_role.id)
        .first()
    )
    if existing_super_admin is not None:
        db.rollback()
        return _result(
            "SUPER_ADMIN_EXISTS",
            "이미 SUPER_ADMIN 사용자가 있어 새로 만들지 않았습니다.",
            login_id=existing_super_admin.login_id,
        )

    existing_user = db.query(User).filter(User.login_id == login_id).one_or_none()
    if existing_user is not None:
        db.rollback()
        return _result(
            "ALREADY_EXISTS",
            "같은 login_id 사용자가 이미 있어 새로 만들지 않았습니다.",
            login_id=login_id,
        )

    password_errors = validate_password_policy(plain_password)
    if plain_password and plain_password.strip() == login_id:
        password_errors.append("login_id와 동일한 비밀번호는 사용할 수 없습니다.")
    if password_errors:
        db.rollback()
        return _result(
            "PASSWORD_POLICY_FAILED",
            "비밀번호 정책을 통과하지 못했습니다.",
            errors=password_errors,
        )

    try:
        user = User(
            login_id=login_id,
            user_name=user_name,
            email=email,
            password_hash=hash_password(plain_password),
            must_change_password=True,
            active_yn=True,
        )
        db.add(user)
        db.flush()

        db.add(UserRole(user_id=user.id, role_id=super_admin_role.id))
        db.commit()
    except Exception:
        db.rollback()
        return _result("ERROR", "SUPER_ADMIN bootstrap 처리 중 오류가 발생했습니다.")

    return _result(
        "CREATED",
        "SUPER_ADMIN 사용자를 생성했습니다.",
        login_id=login_id,
        user_id=user.id,
        must_change_password=True,
    )
