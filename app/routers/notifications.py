from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.core.errors import not_found
from app.core.pagination import paginate
from app.schemas.notifications import (
    MarkReadRequest,
    NotificationListResponse,
)
from app.services.store import UserRecord, store

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    unread: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    cursor: str | None = Query(default=None),
    user: UserRecord = Depends(get_current_user),
) -> dict:
    items = list(store.notifications.get(user.id, []))
    if unread:
        items = [n for n in items if not n["read"]]
    items.sort(key=lambda n: n["createdAt"], reverse=True)
    return paginate(items, limit, cursor)


@router.post("/read", response_model=NotificationListResponse)
def mark_read(body: MarkReadRequest, user: UserRecord = Depends(get_current_user)) -> dict:
    items = store.notifications.get(user.id, [])
    ids = set(body.ids) if body.ids is not None else None
    for n in items:
        if ids is None or n["id"] in ids:
            n["read"] = True
    ordered = sorted(items, key=lambda n: n["createdAt"], reverse=True)
    return {"items": ordered, "nextCursor": None, "total": len(ordered)}


@router.delete("/{notification_id}", status_code=204, response_model=None)
def delete_notification(notification_id: str, user: UserRecord = Depends(get_current_user)) -> None:
    items = store.notifications.get(user.id, [])
    idx = next((i for i, n in enumerate(items) if n["id"] == notification_id), None)
    if idx is None:
        raise not_found("Notification not found.")
    items.pop(idx)
