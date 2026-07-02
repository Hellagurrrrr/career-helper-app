from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.core.errors import not_found
from app.core.pagination import paginate
from app.db import get_conn
from app.models import UserRecord
from app.repositories import notifications as notifications_repo
from app.schemas.notifications import (
    MarkReadRequest,
    NotificationListResponse,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    unread: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    cursor: str | None = Query(default=None),
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    """List the user's notifications newest first, optionally unread-only, paginated."""
    items = notifications_repo.list_for_user(conn, user.id, unread)
    return paginate(items, limit, cursor)


@router.post("/read", response_model=NotificationListResponse)
def mark_read(
    body: MarkReadRequest,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    """Mark notifications read (all of the user's when no ids are given)."""
    items = notifications_repo.mark_read(conn, user.id, body.ids)
    return {"items": items, "nextCursor": None, "total": len(items)}


@router.delete("/{notification_id}", status_code=204, response_model=None)
def delete_notification(
    notification_id: str,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> None:
    """Delete one of the user's notifications; 404 if unknown."""
    if not notifications_repo.delete(conn, user.id, notification_id):
        raise not_found("Notification not found.")
