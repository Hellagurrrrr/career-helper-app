"""User settings repository.

Single-row-per-user preferences in the ``user_settings`` table. ``get`` returns
the stored row or a default (no phantom row is written on read); ``set_enabled``
upserts just that user's row instead of rewriting the whole table.

Rows are returned as snake_case dicts; the API boundary
(``app.schemas.settings.NotificationPreferences``) maps them to camelCase JSON.
"""

from __future__ import annotations

import sqlite3
from typing import Any

# Defaults for a user who has never changed their preferences (matches the
# legacy store's ensure_user_buckets seed).
DEFAULT: dict[str, Any] = {"notifications_enabled": True, "updated_at": 0}


def _row_to_settings(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "notifications_enabled": bool(row["notifications_enabled"]),
        "updated_at": row["updated_at"],
    }


def get(conn: sqlite3.Connection, user_id: str) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,)).fetchone()
    return _row_to_settings(row) if row else dict(DEFAULT)


def set_enabled(
    conn: sqlite3.Connection, user_id: str, enabled: bool, updated_at: int
) -> dict[str, Any]:
    conn.execute(
        "INSERT INTO user_settings(user_id, notifications_enabled, updated_at) VALUES(?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET "
        "notifications_enabled = excluded.notifications_enabled, updated_at = excluded.updated_at",
        (user_id, int(bool(enabled)), updated_at),
    )
    return {"notifications_enabled": bool(enabled), "updated_at": updated_at}
