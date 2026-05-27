"""JWT access token 발급과 검증 유틸."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import InvalidTokenError, TokenExpiredError


JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"


def get_token_expire_at(minutes: int) -> datetime:
    """현재 시각 기준 access token 만료 시각을 계산한다."""

    return datetime.now(UTC) + timedelta(minutes=minutes)


def create_access_token(subject: str, expires_delta_minutes: int | None = None) -> str:
    """사용자 식별자를 subject로 담은 access token을 만든다."""

    settings = get_settings()
    expire_minutes = expires_delta_minutes or settings.access_token_expire_minutes
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": ACCESS_TOKEN_TYPE,
        "iat": int(now.timestamp()),
        "exp": int(get_token_expire_at(expire_minutes).timestamp()),
    }
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    signing_input = ".".join(
        [
            _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8")),
            _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")),
        ]
    )
    signature = hmac.new(settings.secret_key.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_base64url_encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    """access token을 검증하고 payload를 반환한다."""

    try:
        header_text, payload_text, signature_text = token.split(".", 2)
        signing_input = f"{header_text}.{payload_text}"
        settings = get_settings()
        expected_signature = hmac.new(
            settings.secret_key.encode("utf-8"),
            signing_input.encode("ascii"),
            hashlib.sha256,
        ).digest()
        received_signature = _base64url_decode(signature_text)
        if not hmac.compare_digest(received_signature, expected_signature):
            raise InvalidTokenError()

        header = json.loads(_base64url_decode(header_text))
        payload = json.loads(_base64url_decode(payload_text))
    except (ValueError, json.JSONDecodeError) as exc:
        raise InvalidTokenError() from exc

    if header.get("alg") != JWT_ALGORITHM:
        raise InvalidTokenError()
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise InvalidTokenError()
    if not payload.get("sub"):
        raise InvalidTokenError("인증 토큰에 사용자 정보가 없습니다.")
    if int(payload.get("exp", 0)) < int(datetime.now(UTC).timestamp()):
        raise TokenExpiredError()
    return payload


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))
