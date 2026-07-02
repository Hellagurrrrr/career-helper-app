"""User goals repository (``user_goals`` + ``user_goal_confidence`` child).

Per-row SQL: creating/updating a goal touches only that goal's rows, and
``delete``/``delete_all_for_user`` rely on FK ``ON DELETE CASCADE`` to drop the
goal's confidence, tracking, saved jobs and applications -- no full-table rewrite.

The goal working-dict stays in the camelCase shape used by the schema
(``app.schemas.goals.UserGoal``) and the router; the repo maps it to/from the
snake_case columns.
"""

from __future__ import annotations

import sqlite3
from typing import Any


def _row_to_goal(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    confidence = {
        c["skill_id"]: c["score"]
        for c in conn.execute(
            "SELECT skill_id, score FROM user_goal_confidence WHERE goal_id = ?", (row["id"],)
        )
    }
    return {
        "id": row["id"],
        "catalogId": row["catalog_id"],
        "title": row["title"],
        "description": row["description"],
        "color": row["color"],
        "status": row["status"],
        "progress": row["progress"],
        "lastUpdated": row["last_updated"],
        "createdAt": row["created_at"],
        "confidence": confidence,
        "sortOrder": row["sort_order"],
    }


def list_for_user(conn: sqlite3.Connection, user_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM user_goals WHERE user_id = ? ORDER BY sort_order", (user_id,)
    ).fetchall()
    return [_row_to_goal(conn, r) for r in rows]


def get(conn: sqlite3.Connection, user_id: str, goal_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM user_goals WHERE user_id = ? AND id = ?", (user_id, goal_id)
    ).fetchone()
    return _row_to_goal(conn, row) if row else None


def exists(conn: sqlite3.Connection, user_id: str, goal_id: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM user_goals WHERE user_id = ? AND id = ? LIMIT 1", (user_id, goal_id)
        ).fetchone()
        is not None
    )


def has_catalog(conn: sqlite3.Connection, user_id: str, catalog_id: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM user_goals WHERE user_id = ? AND catalog_id = ? LIMIT 1",
            (user_id, catalog_id),
        ).fetchone()
        is not None
    )


def count_for_user(conn: sqlite3.Connection, user_id: str) -> int:
    return conn.execute("SELECT COUNT(*) FROM user_goals WHERE user_id = ?", (user_id,)).fetchone()[
        0
    ]


def create(conn: sqlite3.Connection, user_id: str, goal: dict[str, Any]) -> dict[str, Any]:
    conn.execute(
        "INSERT INTO user_goals"
        "(id, user_id, catalog_id, title, description, color, status, progress, last_updated, created_at, sort_order) "
        "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            goal["id"],
            user_id,
            goal["catalogId"],
            goal["title"],
            goal["description"],
            goal["color"],
            goal["status"],
            goal.get("progress", 0),
            goal.get("lastUpdated", ""),
            goal.get("createdAt", 0),
            goal.get("sortOrder", 0),
        ),
    )
    for skill_id, score in goal.get("confidence", {}).items():
        conn.execute(
            "INSERT OR REPLACE INTO user_goal_confidence(goal_id, skill_id, score) VALUES(?, ?, ?)",
            (goal["id"], skill_id, score),
        )
    return goal


def set_status(conn: sqlite3.Connection, user_id: str, goal_id: str, status: str) -> None:
    conn.execute(
        "UPDATE user_goals SET status = ? WHERE user_id = ? AND id = ?", (status, user_id, goal_id)
    )


def update_confidence(conn: sqlite3.Connection, goal_id: str, confidence: dict[str, int]) -> None:
    for skill_id, score in confidence.items():
        conn.execute(
            "INSERT OR REPLACE INTO user_goal_confidence(goal_id, skill_id, score) VALUES(?, ?, ?)",
            (goal_id, skill_id, score),
        )


def set_progress(conn: sqlite3.Connection, goal_id: str, progress: int, last_updated: str) -> None:
    conn.execute(
        "UPDATE user_goals SET progress = ?, last_updated = ? WHERE id = ?",
        (progress, last_updated, goal_id),
    )


def delete(conn: sqlite3.Connection, user_id: str, goal_id: str) -> bool:
    """Delete a goal. Confidence/tracking/saved-jobs/applications cascade via FK."""
    cur = conn.execute("DELETE FROM user_goals WHERE user_id = ? AND id = ?", (user_id, goal_id))
    return cur.rowcount > 0


def delete_all_for_user(conn: sqlite3.Connection, user_id: str) -> None:
    conn.execute("DELETE FROM user_goals WHERE user_id = ?", (user_id,))


def reorder(conn: sqlite3.Connection, user_id: str, ordered_ids: list[str]) -> None:
    for idx, goal_id in enumerate(ordered_ids):
        conn.execute(
            "UPDATE user_goals SET sort_order = ? WHERE user_id = ? AND id = ?",
            (idx, user_id, goal_id),
        )


def repack_sort_order(conn: sqlite3.Connection, user_id: str) -> None:
    """Renumber a user's goals 0..n-1 by current order (after a delete)."""
    ids = [
        r["id"]
        for r in conn.execute(
            "SELECT id FROM user_goals WHERE user_id = ? ORDER BY sort_order", (user_id,)
        )
    ]
    reorder(conn, user_id, ids)
