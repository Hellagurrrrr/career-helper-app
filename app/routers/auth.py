from __future__ import annotations

import re
import sqlite3

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.errors import (
    account_not_found,
    email_taken,
    unauthorized,
    validation_error,
    wrong_password,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    new_id,
    now_ms,
    verify_password,
)
from app.db import get_conn
from app.models import UserRecord
from app.repositories import auth as auth_repo
from app.schemas.auth import (
    AuthResponse,
    AuthTokens,
    AuthUser,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _to_auth_user(user: UserRecord) -> AuthUser:
    return AuthUser(id=user.id, email=user.email, name=user.name, created_at=user.created_at)


def _issue_tokens(conn: sqlite3.Connection, user_id: str) -> AuthTokens:
    """Mint an access/refresh token pair and register the refresh jti for rotation."""
    jti = new_id("rt")
    auth_repo.add_refresh_token(conn, jti, user_id)
    return AuthTokens(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id, jti),
    )


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(body: RegisterRequest, conn: sqlite3.Connection = Depends(get_conn)) -> AuthResponse:
    """Register a new user; 400 on invalid input, 409 if the email is already taken."""
    name = body.name.strip()
    email = _normalize_email(body.email)

    if not name:
        raise validation_error("Please enter your name.", "name")
    if not body.email.strip():
        raise validation_error("Please enter your email.", "email")
    if not _EMAIL_RE.match(email):
        raise validation_error("Please enter a valid email.", "email")
    if len(body.password) < 6:
        raise validation_error("Password must be at least 6 characters.", "password")
    if auth_repo.email_exists(conn, email):
        raise email_taken("An account with this email already exists.")

    user = UserRecord(
        id=new_id("u"),
        email=email,
        name=name,
        password_hash=hash_password(body.password),
        created_at=now_ms(),
    )
    auth_repo.create_user(conn, user)

    return AuthResponse(user=_to_auth_user(user), tokens=_issue_tokens(conn, user.id))


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, conn: sqlite3.Connection = Depends(get_conn)) -> AuthResponse:
    """Authenticate by email + password and return the user with a fresh token pair."""
    email = _normalize_email(body.email)
    user = auth_repo.get_user_by_email(conn, email)
    if not user:
        raise account_not_found("No account found for this email.")
    if not verify_password(body.password, user.password_hash):
        raise wrong_password("Incorrect password.")
    return AuthResponse(user=_to_auth_user(user), tokens=_issue_tokens(conn, user.id))


@router.post("/refresh", response_model=AuthTokens)
def refresh(body: RefreshRequest, conn: sqlite3.Connection = Depends(get_conn)) -> AuthTokens:
    """Rotate a valid refresh token into a new pair; 401 if it was revoked."""
    payload = decode_token(body.refresh_token, expected_type="refresh")
    jti = payload.get("jti")
    user_id = payload.get("sub")
    if (
        not jti
        or auth_repo.refresh_token_user(conn, jti) != user_id
        or auth_repo.get_user(conn, user_id) is None
    ):
        raise unauthorized("Refresh token has been revoked.")
    # Rotate: revoke the old jti and issue a fresh pair.
    auth_repo.revoke_refresh_token(conn, jti)
    return _issue_tokens(conn, user_id)


@router.post("/logout", status_code=204, response_model=None)
def logout(
    body: RefreshRequest,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> None:
    """Revoke the supplied refresh token so it can no longer be rotated."""
    payload = decode_token(body.refresh_token, expected_type="refresh")
    jti = payload.get("jti")
    if jti:
        auth_repo.revoke_refresh_token(conn, jti)


@router.get("/me", response_model=AuthUser)
def me(user: UserRecord = Depends(get_current_user)) -> AuthUser:
    """Return the authenticated user."""
    return _to_auth_user(user)
