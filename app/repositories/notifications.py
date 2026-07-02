"""Notifications repository.

Direct, per-row SQL against the ``notifications`` table. Reads are ordered and
filtered in SQL; writes insert a single row and trim the per-user history to the
most recent ``MAX_NOTIFICATIONS`` instead of rewriting the whole bucket.

Rows are returned as snake_case dicts; the API boundary
(``app.schemas.notifications``) maps them to camelCase JSON.
"""

from __future__ import annotations

import sqlite3
from typing import Any

MAX_NOTIFICATIONS = 50  # api-design 11.2: keep the most recent 50 per user


def _row_to_notification(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "type": row["type"],
        "severity": row["severity"],
        "title": row["title"],
        "body": row["body"],
        "link": row["link"],
        "created_at": row["created_at"],
        "read": bool(row["read"]),
        "dedup_key": row["dedup_key"],
    }


def list_for_user(
    conn: sqlite3.Connection, user_id: str, unread: bool | None = None
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM notifications WHERE user_id = ?"
    params: list[Any] = [user_id]
    if unread:
        sql += " AND read = 0"
    sql += " ORDER BY created_at DESC"
    return [_row_to_notification(r) for r in conn.execute(sql, params)]


def add(
    conn: sqlite3.Connection,
    user_id: str,
    *,
    notification_id: str,
    type: str,
    severity: str,
    title: str,
    body: str,
    created_at: int,
    link: str | None = None,
    dedup_key: str | None = None,
) -> dict[str, Any] | None:
    """Insert a notification, de-duplicating by (user_id, dedup_key).

    Returns the created row, or ``None`` if a row with the same dedup_key already
    exists for the user.
    """
    if dedup_key is not None:
        existing = conn.execute(
            "SELECT 1 FROM notifications WHERE user_id = ? AND dedup_key = ? LIMIT 1",
            (user_id, dedup_key),
        ).fetchone()
        if existing:
            return None

    conn.execute(
        "INSERT INTO notifications(id, user_id, type, severity, title, body, link, created_at, read, dedup_key) "
        "VALUES(?, ?, ?, ?, ?, ?, ?, ?, 0, ?)",
        (notification_id, user_id, type, severity, title, body, link, created_at, dedup_key),
    )
    # Trim to the most recent MAX_NOTIFICATIONS for this user.
    conn.execute(
        "DELETE FROM notifications WHERE user_id = ? AND id NOT IN ("
        "  SELECT id FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT ?"
        ")",
        (user_id, user_id, MAX_NOTIFICATIONS),
    )
    row = conn.execute("SELECT * FROM notifications WHERE id = ?", (notification_id,)).fetchone()
    return _row_to_notification(row) if row else None


def mark_read(
    conn: sqlite3.Connection, user_id: str, ids: list[str] | None = None
) -> list[dict[str, Any]]:
    """Mark the given notifications read (all of the user's when ``ids`` is None).

    Returns the user's full notification list, newest first.
    """
    if ids is None:
        conn.execute("UPDATE notifications SET read = 1 WHERE user_id = ?", (user_id,))
    elif ids:
        placeholders = ",".join("?" * len(ids))
        conn.execute(
            f"UPDATE notifications SET read = 1 WHERE user_id = ? AND id IN ({placeholders})",
            (user_id, *ids),
        )
    return list_for_user(conn, user_id)


def delete(conn: sqlite3.Connection, user_id: str, notification_id: str) -> bool:
    cur = conn.execute(
        "DELETE FROM notifications WHERE user_id = ? AND id = ?", (user_id, notification_id)
    )
    return cur.rowcount > 0


def delete_for_user(conn: sqlite3.Connection, user_id: str) -> None:
    conn.execute("DELETE FROM notifications WHERE user_id = ?", (user_id,))
