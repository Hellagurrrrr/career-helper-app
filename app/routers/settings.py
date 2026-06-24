from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.errors import validation_error, wrong_password
from app.core.security import hash_password, now_ms, verify_password
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


def _notification_preferences(user_id: str) -> dict:
    store.ensure_user_buckets(user_id)
    return store.user_settings[user_id]


def _settings_response(user: UserRecord) -> SettingsResponse:
    prefs = _notification_preferences(user.id)
    return SettingsResponse(
        account=SettingsAccount(
            id=user.id,
            email=user.email,
            name=user.name,
            created_at=user.created_at,
        ),
        notifications=NotificationPreferences(
            enabled=bool(prefs.get("notificationsEnabled", True)),
            updated_at=int(prefs.get("updatedAt", 0)),
        ),
    )


@router.get("", response_model=SettingsResponse)
def get_settings(user: UserRecord = Depends(get_current_user)) -> SettingsResponse:
    """Return read-only account data and stored settings preferences."""
    return _settings_response(user)


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
) -> NotificationPreferences:
    """Persist the in-app notification toggle (use-case SET-06)."""
    prefs = {"notificationsEnabled": body.enabled, "updatedAt": now_ms()}
    store.user_settings[user.id] = prefs
    return NotificationPreferences(enabled=prefs["notificationsEnabled"], updated_at=prefs["updatedAt"])


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
