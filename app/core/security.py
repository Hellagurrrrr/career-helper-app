from __future__ import annotations

import time
import uuid
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings
from app.core.errors import unauthorized

# bcrypt only hashes the first 72 bytes; truncate to stay within that limit.
_BCRYPT_MAX_BYTES = 72


def now_ms() -> int:
    """Current time in Unix milliseconds (api-design 1.1 time format)."""
    return int(time.time() * 1000)


def new_id(prefix: str = "") -> str:
    short = uuid.uuid4().hex[:12]
    return f"{prefix}_{short}" if prefix else short


def _encode_password(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_encode_password(password), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_encode_password(password), hashed.encode("ascii"))
    except (ValueError, TypeError):
        return False


def _encode(claims: dict[str, Any], ttl_seconds: int, token_type: str) -> str:
    now = int(time.time())
    payload = {
        **claims,
        "type": token_type,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: str) -> str:
    return _encode({"sub": user_id}, settings.access_token_ttl_seconds, "access")


def create_refresh_token(user_id: str, jti: str) -> str:
    return _encode({"sub": user_id, "jti": jti}, settings.refresh_token_ttl_seconds, "refresh")


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise unauthorized("Invalid or expired token.")
    if payload.get("type") != expected_type:
        raise unauthorized("Invalid token type.")
    return payload
