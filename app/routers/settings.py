from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.errors import validation_error, wrong_password
from app.core.security import hash_password, now_ms, verify_password
from app.db import get_conn
from app.repositories import user_settings as user_settings_repo
from app.schemas.settings import (
    ChangePasswordRequest,
    NotificationPreferences,
    NotificationPreferencesRequest,
    SettingsAccount,
    SettingsResponse,
    SettingsStatusResponse,
)
from app.services.store import UserRecord, store

router = APIRouter(prefix="/settings", tags=["settings"])


def _settings_response(user: UserRecord, conn: sqlite3.Connection) -> SettingsResponse:
    prefs = user_settings_repo.get(conn, user.id)
    return SettingsResponse(
        account=SettingsAccount(
            id=user.id,
            email=user.email,
            name=user.name,
            created_at=user.created_at,
        ),
        notifications=NotificationPreferences(
            enabled=prefs["notifications_enabled"],
            updated_at=prefs["updated_at"],
        ),
    )


@router.get("", response_model=SettingsResponse)
def get_settings(
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> SettingsResponse:
    """Return read-only account data and stored settings preferences."""
    return _settings_response(user, conn)


@router.post("/password", response_model=SettingsStatusResponse)
def change_password(
    body: ChangePasswordRequest,
    user: UserRecord = Depends(get_current_user),
) -> SettingsStatusResponse:
    """Change the current account password (use-cases SET-03~05)."""
    if len(body.new_password) < 6:
        raise validation_error("New password must be at least 6 characters.", "newPassword")
    if not verify_password(body.current_password, user.password_hash):
        raise wrong_password("Current password is incorrect.")

    store.update_user_password(user.id, hash_password(body.new_password))
    store.revoke_refresh_tokens_for_user(user.id)
    return SettingsStatusResponse(status="updated")


@router.put("/notifications", response_model=NotificationPreferences)
def update_notification_preferences(
    body: NotificationPreferencesRequest,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> NotificationPreferences:
    """Persist the in-app notification toggle (use-case SET-06)."""
    prefs = user_settings_repo.set_enabled(conn, user.id, body.enabled, now_ms())
    return NotificationPreferences(
        enabled=prefs["notifications_enabled"], updated_at=prefs["updated_at"]
    )


@router.post("/reset-demo-data", response_model=SettingsStatusResponse)
def reset_demo_data(user: UserRecord = Depends(get_current_user)) -> SettingsStatusResponse:
    """Clear demo data while preserving the account and settings (use-case SET-07)."""
    store.reset_user_data(user.id)
    store.ensure_user_buckets(user.id)
    return SettingsStatusResponse(status="reset")


@router.delete("/account", status_code=204, response_model=None)
def delete_account(user: UserRecord = Depends(get_current_user)) -> None:
    """Delete the account and all user-owned demo data (use-case SET-08)."""
    store.delete_account(user.id)
