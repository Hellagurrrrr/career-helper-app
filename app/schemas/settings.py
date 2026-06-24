from __future__ import annotations

from app.schemas.common import CamelModel


class SettingsAccount(CamelModel):
    id: str
    email: str
    name: str
    created_at: int


class NotificationPreferences(CamelModel):
    enabled: bool
    updated_at: int


class SettingsResponse(CamelModel):
    account: SettingsAccount
    notifications: NotificationPreferences


class ChangePasswordRequest(CamelModel):
    current_password: str = ""
    new_password: str = ""


class NotificationPreferencesRequest(CamelModel):
    enabled: bool


class SettingsStatusResponse(CamelModel):
    status: str
