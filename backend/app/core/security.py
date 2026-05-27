"""비밀번호 해시와 최소 정책 검증 유틸."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import secrets


_PASSWORD_ALGORITHM = "pbkdf2_sha256"
_PASSWORD_ITERATIONS = 390_000
_SALT_BYTES = 16


def validate_password_policy(plain_password: str) -> list[str]:
    """P0 단계의 최소 비밀번호 정책 위반 사유를 반환한다."""

    errors: list[str] = []
    if plain_password is None:
        return ["비밀번호를 입력해야 합니다."]

    if plain_password == "":
        errors.append("비밀번호를 입력해야 합니다.")
    if plain_password.strip() == "":
        errors.append("비밀번호는 공백만 사용할 수 없습니다.")
    if len(plain_password) < 8:
        errors.append("비밀번호는 8자 이상이어야 합니다.")
    return errors


def hash_password(plain_password: str) -> str:
    """평문 비밀번호를 저장용 해시 문자열로 변환한다."""

    errors = validate_password_policy(plain_password)
    if errors:
        raise ValueError("비밀번호 정책을 통과하지 못했습니다.")

    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt,
        _PASSWORD_ITERATIONS,
    )
    salt_text = base64.urlsafe_b64encode(salt).decode("ascii")
    digest_text = base64.urlsafe_b64encode(digest).decode("ascii")
    return f"{_PASSWORD_ALGORITHM}${_PASSWORD_ITERATIONS}${salt_text}${digest_text}"


def verify_password(plain_password: str, password_hash: str) -> bool:
    """평문 비밀번호가 저장된 해시와 일치하는지만 반환한다."""

    try:
        algorithm, iterations_text, salt_text, digest_text = password_hash.split("$", 3)
        if algorithm != _PASSWORD_ALGORITHM:
            return False
        iterations = int(iterations_text)
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected_digest = base64.urlsafe_b64decode(digest_text.encode("ascii"))
    except (binascii.Error, ValueError, TypeError):
        return False

    candidate_digest = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(candidate_digest, expected_digest)
