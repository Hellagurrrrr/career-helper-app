"""Applications repository.

Per-row SQL over ``applications``. Deleting an application cascades (FK) to its
interview reviews and mock sessions. The app working-dict keeps the camelCase
shape used by the schema and routers; the repo maps it to/from snake columns.

(The ``cv_text`` column is write-rarely / never read back into the working dict,
matching the legacy mirror, so it is left NULL here.)
"""

from __future__ import annotations

import sqlite3
from typing import Any


def _row_to_app(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "kind": row["kind"],
        "goalId": row["goal_id"],
        "jobId": row["job_id"],
        "title": row["title"],
        "company": row["company"],
        "submittedAt": row["submitted_at"],
        "partnerStatus": row["partner_status"],
        "manualStatus": row["manual_status"],
    }


def list_for_user(conn: sqlite3.Connection, user_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM applications WHERE user_id = ? ORDER BY submitted_at DESC", (user_id,)
    ).fetchall()
    return [_row_to_app(r) for r in rows]


def get(conn: sqlite3.Connection, user_id: str, app_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM applications WHERE user_id = ? AND id = ?", (user_id, app_id)
    ).fetchone()
    return _row_to_app(row) if row else None


def count_for_user(conn: sqlite3.Connection, user_id: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM applications WHERE user_id = ?", (user_id,)
    ).fetchone()[0]


def has_job(conn: sqlite3.Connection, user_id: str, job_id: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM applications WHERE user_id = ? AND job_id = ? LIMIT 1", (user_id, job_id)
        ).fetchone()
        is not None
    )


def create(conn: sqlite3.Connection, user_id: str, app: dict[str, Any]) -> dict[str, Any]:
    conn.execute(
        "INSERT INTO applications"
        "(id, user_id, kind, goal_id, job_id, title, company, submitted_at, partner_status, manual_status, cv_text) "
        "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
        (
            app["id"],
            user_id,
            app["kind"],
            app["goalId"],
            app["jobId"],
            app["title"],
            app["company"],
            app["submittedAt"],
            app.get("partnerStatus"),
            app.get("manualStatus"),
        ),
    )
    return app


def set_manual_status(
    conn: sqlite3.Connection, user_id: str, app_id: str, status: str | None
) -> None:
    conn.execute(
        "UPDATE applications SET manual_status = ? WHERE user_id = ? AND id = ?",
        (status, user_id, app_id),
    )


def set_partner_status(conn: sqlite3.Connection, app_id: str, status: str) -> None:
    conn.execute("UPDATE applications SET partner_status = ? WHERE id = ?", (status, app_id))


def delete(conn: sqlite3.Connection, user_id: str, app_id: str) -> bool:
    """Delete an application. Reviews and mock sessions cascade via FK."""
    cur = conn.execute("DELETE FROM applications WHERE user_id = ? AND id = ?", (user_id, app_id))
    return cur.rowcount > 0
