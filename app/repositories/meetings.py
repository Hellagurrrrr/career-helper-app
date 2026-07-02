"""Meetings repository.

Direct, per-row SQL against ``meetings`` and ``meeting_preferred_times``. Every
function touches only the rows it needs -- creating one meeting inserts one row
(plus its preferred-time children), not a rewrite of every user's meetings.

Rows are returned as snake_case dicts. The API boundary
(``app.schemas.alumni.MeetingRequest``) maps them to camelCase JSON, so the
persistence layer stays free of serialization concerns.
"""

from __future__ import annotations

import sqlite3
from typing import Any

# Sentinel so ``set_status`` can leave ``completed_at`` untouched when the caller
# does not pass it (distinct from explicitly setting it to NULL).
_UNSET = object()


def _row_to_meeting(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    preferred_times = [
        r["preferred_time"]
        for r in conn.execute(
            "SELECT preferred_time FROM meeting_preferred_times "
            "WHERE meeting_id = ? ORDER BY sort_order",
            (row["id"],),
        )
    ]
    return {
        "id": row["id"],
        "alumni_id": row["alumni_id"],
        "topic": row["topic"],
        "message": row["message"],
        "preferred_times": preferred_times,
        "submitted_at": row["submitted_at"],
        "status": row["status"],
        "completed_at": row["completed_at"],
    }


def list_for_user(
    conn: sqlite3.Connection, user_id: str, alumni_id: str | None = None
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM meetings WHERE user_id = ?"
    params: list[Any] = [user_id]
    if alumni_id is not None:
        sql += " AND alumni_id = ?"
        params.append(alumni_id)
    sql += " ORDER BY submitted_at DESC"
    rows = conn.execute(sql, params).fetchall()
    return [_row_to_meeting(conn, row) for row in rows]


def get(conn: sqlite3.Connection, user_id: str, meeting_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM meetings WHERE user_id = ? AND id = ?", (user_id, meeting_id)
    ).fetchone()
    return _row_to_meeting(conn, row) if row else None


def has_pending_with_alumni(conn: sqlite3.Connection, user_id: str, alumni_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM meetings WHERE user_id = ? AND alumni_id = ? AND status = 'pending' LIMIT 1",
        (user_id, alumni_id),
    ).fetchone()
    return row is not None


def create(
    conn: sqlite3.Connection,
    *,
    meeting_id: str,
    user_id: str,
    alumni_id: str,
    topic: str,
    message: str,
    preferred_times: list[str],
    submitted_at: int,
) -> dict[str, Any]:
    conn.execute(
        "INSERT INTO meetings(id, user_id, alumni_id, topic, message, submitted_at, status, completed_at) "
        "VALUES(?, ?, ?, ?, ?, ?, 'pending', NULL)",
        (meeting_id, user_id, alumni_id, topic, message, submitted_at),
    )
    for idx, preferred in enumerate(preferred_times):
        conn.execute(
            "INSERT INTO meeting_preferred_times(meeting_id, preferred_time, sort_order) VALUES(?, ?, ?)",
            (meeting_id, preferred, idx),
        )
    created = get(conn, user_id, meeting_id)
    assert created is not None  # just inserted
    return created


def set_status(
    conn: sqlite3.Connection,
    user_id: str,
    meeting_id: str,
    status: str,
    completed_at: Any = _UNSET,
) -> dict[str, Any] | None:
    if completed_at is _UNSET:
        cur = conn.execute(
            "UPDATE meetings SET status = ? WHERE user_id = ? AND id = ?",
            (status, user_id, meeting_id),
        )
    else:
        cur = conn.execute(
            "UPDATE meetings SET status = ?, completed_at = ? WHERE user_id = ? AND id = ?",
            (status, completed_at, user_id, meeting_id),
        )
    if cur.rowcount == 0:
        return None
    return get(conn, user_id, meeting_id)


def delete_for_user(conn: sqlite3.Connection, user_id: str) -> None:
    """Delete all of a user's meetings (preferred-time rows cascade via FK)."""
    conn.execute("DELETE FROM meetings WHERE user_id = ?", (user_id,))
