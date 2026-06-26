"""Mock interview repository (``mock_interview_sessions`` + ``mock_interview_turns``).

``create`` inserts a session and its turns; ``save`` updates the session's mutable
fields and replaces its turns (the conversation grows turn-by-turn). Scoped per
session, not a whole-table rewrite. JSON columns hold skills/dimensions/questions.

Working dicts keep the camelCase shape used by ``app.schemas.coaching``.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any


def _from_json(value: str | None, default: Any) -> Any:
    return json.loads(value) if value not in (None, "") else default


def _row_to_session(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    session = {
        "id": row["id"],
        "applicationId": row["application_id"],
        "jobTitle": row["job_title"],
        "company": row["company"],
        "goalTitle": row["goal_title"],
        "skills": _from_json(row["skills_json"], []),
        "startedAt": row["started_at"],
        "completedAt": row["completed_at"],
        "durationSec": row["duration_sec"],
        "turns": [],
        "transcript": row["transcript"],
        "overallSummary": row["overall_summary"],
        "dimensions": _from_json(row["dimensions_json"], []),
        "improvementAdvice": row["improvement_advice"],
        "questions": _from_json(row["questions_json"], []),
        "currentIndex": row["current_index"],
        "status": row["status"],
        "error": row["error"],
    }
    for turn in conn.execute(
        "SELECT * FROM mock_interview_turns WHERE session_id = ? ORDER BY sort_order", (row["id"],)
    ):
        session["turns"].append(
            {"id": turn["id"], "role": turn["role"], "text": turn["text"], "timestamp": turn["timestamp"]}
        )
    return session


def list_for_app(conn: sqlite3.Connection, user_id: str, app_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM mock_interview_sessions WHERE user_id = ? AND application_id = ? "
        "ORDER BY started_at DESC",
        (user_id, app_id),
    ).fetchall()
    return [_row_to_session(conn, r) for r in rows]


def get(conn: sqlite3.Connection, user_id: str, session_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM mock_interview_sessions WHERE user_id = ? AND id = ?", (user_id, session_id)
    ).fetchone()
    return _row_to_session(conn, row) if row else None


def count_for_user(conn: sqlite3.Connection, user_id: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM mock_interview_sessions WHERE user_id = ?", (user_id,)
    ).fetchone()[0]


def count_for_app(conn: sqlite3.Connection, user_id: str, app_id: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM mock_interview_sessions WHERE user_id = ? AND application_id = ?",
        (user_id, app_id),
    ).fetchone()[0]


def create(conn: sqlite3.Connection, user_id: str, session: dict[str, Any]) -> dict[str, Any]:
    conn.execute(
        "INSERT INTO mock_interview_sessions"
        "(id, user_id, application_id, job_title, company, goal_title, skills_json, status, started_at, "
        "completed_at, duration_sec, transcript, overall_summary, dimensions_json, improvement_advice, "
        "questions_json, current_index, error) "
        "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (session["id"], user_id, session["applicationId"], session.get("jobTitle", ""),
         session.get("company", ""), session.get("goalTitle"), json.dumps(session.get("skills", [])),
         session.get("status", "in_progress"), session.get("startedAt", 0), session.get("completedAt"),
         session.get("durationSec"), session.get("transcript", ""), session.get("overallSummary", ""),
         json.dumps(session.get("dimensions", [])), session.get("improvementAdvice", ""),
         json.dumps(session.get("questions", [])), session.get("currentIndex", 0), session.get("error")),
    )
    _replace_turns(conn, session)
    return session


def save(conn: sqlite3.Connection, session: dict[str, Any]) -> None:
    """Update a session's mutable fields and replace its turns (identified by id)."""
    conn.execute(
        "UPDATE mock_interview_sessions SET status = ?, completed_at = ?, duration_sec = ?, "
        "transcript = ?, overall_summary = ?, dimensions_json = ?, improvement_advice = ?, "
        "questions_json = ?, current_index = ?, error = ? WHERE id = ?",
        (session.get("status", "in_progress"), session.get("completedAt"), session.get("durationSec"),
         session.get("transcript", ""), session.get("overallSummary", ""),
         json.dumps(session.get("dimensions", [])), session.get("improvementAdvice", ""),
         json.dumps(session.get("questions", [])), session.get("currentIndex", 0), session.get("error"),
         session["id"]),
    )
    _replace_turns(conn, session)


def _replace_turns(conn: sqlite3.Connection, session: dict[str, Any]) -> None:
    conn.execute("DELETE FROM mock_interview_turns WHERE session_id = ?", (session["id"],))
    for idx, turn in enumerate(session.get("turns", [])):
        conn.execute(
            "INSERT INTO mock_interview_turns(id, session_id, role, text, timestamp, sort_order) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            (turn["id"], session["id"], turn["role"], turn["text"], turn["timestamp"], idx),
        )


def delete(conn: sqlite3.Connection, user_id: str, app_id: str, session_id: str) -> bool:
    cur = conn.execute(
        "DELETE FROM mock_interview_sessions WHERE user_id = ? AND application_id = ? AND id = ?",
        (user_id, app_id, session_id),
    )
    return cur.rowcount > 0
