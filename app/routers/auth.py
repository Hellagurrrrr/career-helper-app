from __future__ import annotations

import re

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
from app.schemas.auth import (
    AuthResponse,
    AuthTokens,
    AuthUser,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
)
from app.services.store import UserRecord, store

router = APIRouter(prefix="/auth", tags=["auth"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _to_auth_user(user: UserRecord) -> AuthUser:
    '''
    Convert a user record to an auth user.
    Args:
        user: UserRecord: The user record to convert.
    Returns:
        AuthUser: The auth user.
    '''
    return AuthUser(id=user.id, email=user.email, name=user.name, created_at=user.created_at)


def _issue_tokens(user_id: str) -> AuthTokens:
    '''
    Issue tokens for a user.
    Args:
        user_id: str: The user ID to issue tokens for.
    Returns:
        AuthTokens: The tokens for the user.
    '''
    jti = new_id("rt")
    store.refresh_jti[jti] = user_id
    return AuthTokens(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id, jti),
    )


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(body: RegisterRequest) -> AuthResponse:
    '''
    Register a new user.
    Args:
        body: RegisterRequest: The request body containing the user's name, email, and password.
    Returns:
        AuthResponse: The response containing the user's information and tokens.
    Raises:
        validation_error: If the name, email, or password is invalid.
        email_taken: If the email is already taken.
    '''
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
    if email in store.email_index:
        raise email_taken("An account with this email already exists.")

    user = UserRecord(
        id=new_id("u"),
        email=email,
        name=name,
        password_hash=hash_password(body.password),
        created_at=now_ms(),
    )
    store.users[user.id] = user
    store.email_index[email] = user.id
    store.ensure_user_buckets(user.id)

    return AuthResponse(user=_to_auth_user(user), tokens=_issue_tokens(user.id))


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest) -> AuthResponse:
    '''
    Login a user.
    Args:
        body: LoginRequest: The request body containing the user's email and password.
    Returns:
        AuthResponse: The response containing the user's information and tokens.
    Raises:
        account_not_found: If the email is not found.
        wrong_password: If the password is incorrect.
    '''
    email = _normalize_email(body.email)
    user_id = store.email_index.get(email)
    if not user_id:
        raise account_not_found("No account found for this email.")
    user = store.users[user_id]
    if not verify_password(body.password, user.password_hash):
        raise wrong_password("Incorrect password.")
    return AuthResponse(user=_to_auth_user(user), tokens=_issue_tokens(user.id))


@router.post("/refresh", response_model=AuthTokens)
def refresh(body: RefreshRequest) -> AuthTokens:
    '''
    Refresh a user's tokens.
    Args:
        body: RefreshRequest: The request body containing the refresh token.
    Returns:
        AuthTokens: The new tokens for the user.
    Raises:
        unauthorized: If the refresh token has been revoked.
    '''
    payload = decode_token(body.refresh_token, expected_type="refresh")
    jti = payload.get("jti")
    user_id = payload.get("sub")
    if not jti or store.refresh_jti.get(jti) != user_id or user_id not in store.users:
        raise unauthorized("Refresh token has been revoked.")
    # Rotate: revoke the old jti and issue a fresh pair.
    store.refresh_jti.pop(jti, None)
    return _issue_tokens(user_id)


@router.post("/logout", status_code=204, response_model=None)
def logout(body: RefreshRequest, user: UserRecord = Depends(get_current_user)) -> None:
    '''
    Logout a user.
    Args:
        body: RefreshRequest: The request body containing the refresh token.
        user: UserRecord: The current user.
    Returns:
        None: The response is empty.
    Raises:
        unauthorized: If the refresh token has been revoked.
    '''
    payload = decode_token(body.refresh_token, expected_type="refresh")
    jti = payload.get("jti")
    if jti:
        store.refresh_jti.pop(jti, None)


@router.get("/me", response_model=AuthUser)
def me(user: UserRecord = Depends(get_current_user)) -> AuthUser:
    '''
    Get the current user.
    Args:
        user: UserRecord: The current user.
    Returns:
        AuthUser: The current user in auth user schema.
    '''
    return _to_auth_user(user)
