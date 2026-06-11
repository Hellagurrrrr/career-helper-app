from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import unauthorized
from app.core.security import decode_token
from app.services.store import UserRecord, store

# auto_error=False so we can raise the unified UNAUTHORIZED envelope ourselves.
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UserRecord:
    if creds is None or not creds.credentials:
        raise unauthorized("Authentication required.")
    payload = decode_token(creds.credentials, expected_type="access")
    user_id = payload.get("sub")
    user = store.users.get(user_id) if user_id else None
    if user is None:
        raise unauthorized("Account no longer exists.")
    store.ensure_user_buckets(user.id)
    return user
