"""CV extraction task repository.

Transient async-task state in ``cv_extract_tasks``. Each call updates a single
task row (poll counter, stage, draft, error) instead of rewriting the whole
table. ``draft`` is stored as JSON text in ``draft_json``.

Rows are returned as snake_case dicts; the API boundary
(``app.schemas.profile.CvExtractResult``) maps them to camelCase JSON.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any


def _row_to_task(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "file_name": row["file_name"],
        "status": row["status"],
        "stage": row["stage"],
        "draft": json.loads(row["draft_json"]) if row["draft_json"] else None,
        "polls": row["polls"],
        "error": row["error"],
    }


def get(conn: sqlite3.Connection, task_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM cv_extract_tasks WHERE id = ?", (task_id,)).fetchone()
    return _row_to_task(row) if row else None


def create(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    user_id: str,
    file_name: str,
    status: str = "processing",
    stage: str = "parsing",
) -> dict[str, Any]:
    conn.execute(
        "INSERT INTO cv_extract_tasks(id, user_id, file_name, status, stage, polls) "
        "VALUES(?, ?, ?, ?, ?, 0)",
        (task_id, user_id, file_name, status, stage),
    )
    created = get(conn, task_id)
    assert created is not None  # just inserted
    return created


def increment_polls(conn: sqlite3.Connection, task_id: str) -> int | None:
    """Bump the mock poll counter and return the new value (None if missing)."""
    cur = conn.execute("UPDATE cv_extract_tasks SET polls = polls + 1 WHERE id = ?", (task_id,))
    if cur.rowcount == 0:
        return None
    row = conn.execute("SELECT polls FROM cv_extract_tasks WHERE id = ?", (task_id,)).fetchone()
    return row["polls"]


def set_stage(conn: sqlite3.Connection, task_id: str, stage: str) -> None:
    conn.execute("UPDATE cv_extract_tasks SET stage = ? WHERE id = ?", (stage, task_id))


def complete(
    conn: sqlite3.Connection, task_id: str, draft: dict[str, Any] | None, stage: str = "structuring"
) -> None:
    conn.execute(
        "UPDATE cv_extract_tasks SET status = 'complete', stage = ?, draft_json = ? WHERE id = ?",
        (stage, json.dumps(draft) if draft is not None else None, task_id),
    )


def fail(conn: sqlite3.Connection, task_id: str, error: str) -> None:
    conn.execute(
        "UPDATE cv_extract_tasks SET status = 'failed', error = ? WHERE id = ?",
        (error, task_id),
    )
