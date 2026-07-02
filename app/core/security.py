from __future__ import annotations

import time
import uuid
from typing import Any

import bcrypt
import jwt
from jwt import InvalidTokenError

from app.core.config import settings
from app.core.errors import unauthorized

# bcrypt only hashes the first 72 bytes; truncate to stay within that limit.
_BCRYPT_MAX_BYTES = 72


def now_ms() -> int:
    """Current time in Unix milliseconds (api-design 1.1 time format)."""
    return int(time.time() * 1000)


def iso_now() -> str:
    """Current UTC time as an ISO-8601 ``YYYY-MM-DDTHH:MM:SSZ`` string."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str = "") -> str:
    """Generate a new unique ID.

    Args:
        prefix: The prefix for the ID.

    Returns:
        str: The new unique ID.
    """
    short = uuid.uuid4().hex[:12]
    return f"{prefix}_{short}" if prefix else short


def _encode_password(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_encode_password(password), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password.

    Args:
        password: The password to verify.
        hashed: The hashed password to verify against.

    Returns:
        bool: True if the password is correct, False otherwise.

    Raises:
        ValueError: If the password is invalid.
        TypeError: If the hashed password is invalid.
    """
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
    """Decode a token.

    Args:
        token: The token to decode.
        expected_type: The expected type of the token.

    Returns:
        dict[str, Any]: The decoded payload.

    Raises:
        unauthorized: If the token is invalid or expired.
        unauthorized: If the token type is invalid.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except InvalidTokenError:
        raise unauthorized("Invalid or expired token.")
    if payload.get("type") != expected_type:
        raise unauthorized("Invalid token type.")
    return payload
