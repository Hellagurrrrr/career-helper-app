from __future__ import annotations

from typing import Literal

from app.schemas.common import CamelModel


class AppNotification(CamelModel):
    id: str
    type: Literal["system", "job", "alumni", "meeting", "milestone", "week"]
    severity: Literal["info", "success", "warning"]
    title: str
    body: str
    link: str | None = None
    created_at: int
    read: bool
    dedup_key: str | None = None


class NotificationListResponse(CamelModel):
    items: list[AppNotification]
    next_cursor: str | None = None
    total: int


class MarkReadRequest(CamelModel):
    ids: list[str] | None = None
