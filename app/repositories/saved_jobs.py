"""Saved jobs repository.

The ``saved_jobs`` table is a set of (user, goal, job) rows. Each call inserts or
deletes a single row. Rows cascade away when the goal or user is deleted
(``goal_id``/``user_id`` FKs ``ON DELETE CASCADE``).
"""

from __future__ import annotations

import sqlite3

from app.core.security import now_ms


def list_job_ids(conn: sqlite3.Connection, user_id: str, goal_id: str) -> list[str]:
    return [
        r["job_id"]
        for r in conn.execute(
            "SELECT job_id FROM saved_jobs WHERE user_id = ? AND goal_id = ? ORDER BY saved_at, job_id",
            (user_id, goal_id),
        )
    ]


def is_saved(conn: sqlite3.Connection, user_id: str, goal_id: str, job_id: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM saved_jobs WHERE user_id = ? AND goal_id = ? AND job_id = ? LIMIT 1",
            (user_id, goal_id, job_id),
        ).fetchone()
        is not None
    )


def add(conn: sqlite3.Connection, user_id: str, goal_id: str, job_id: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO saved_jobs(user_id, goal_id, job_id, saved_at) VALUES(?, ?, ?, ?)",
        (user_id, goal_id, job_id, now_ms()),
    )


def remove(conn: sqlite3.Connection, user_id: str, goal_id: str, job_id: str) -> bool:
    cur = conn.execute(
        "DELETE FROM saved_jobs WHERE user_id = ? AND goal_id = ? AND job_id = ?",
        (user_id, goal_id, job_id),
    )
    return cur.rowcount > 0
