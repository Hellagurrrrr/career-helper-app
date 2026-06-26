"""Interview reviews repository.

``interview_reviews`` rows, scoped per (user, application). ``create`` inserts one
row; ``save`` updates the mutable analysis fields of one row (the poller / real-AI
background task advance status, transcript, dimensions, etc.). ``dimensions`` is
stored as JSON text.

Working dicts keep the camelCase shape used by ``app.schemas.coaching``.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any


def _from_json(value: str | None, default: Any) -> Any:
    return json.loads(value) if value not in (None, "") else default


def _row_to_review(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "applicationId": row["application_id"],
        "fileName": row["file_name"],
        "uploadedAt": row["uploaded_at"],
        "durationSec": row["duration_sec"],
        "transcript": row["transcript"],
        "overallSummary": row["overall_summary"],
        "dimensions": _from_json(row["dimensions_json"], []),
        "improvementAdvice": row["improvement_advice"],
        "status": row["status"],
        "polls": row["polls"],
        "error": row["error"],
    }


def list_for_app(conn: sqlite3.Connection, user_id: str, app_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM interview_reviews WHERE user_id = ? AND application_id = ? "
        "ORDER BY uploaded_at DESC",
        (user_id, app_id),
    ).fetchall()
    return [_row_to_review(r) for r in rows]


def get(conn: sqlite3.Connection, user_id: str, review_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM interview_reviews WHERE user_id = ? AND id = ?", (user_id, review_id)
    ).fetchone()
    return _row_to_review(row) if row else None


def count_complete_for_user(conn: sqlite3.Connection, user_id: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM interview_reviews WHERE user_id = ? AND status = 'complete'",
        (user_id,),
    ).fetchone()[0]


def count_for_app(conn: sqlite3.Connection, user_id: str, app_id: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM interview_reviews WHERE user_id = ? AND application_id = ?",
        (user_id, app_id),
    ).fetchone()[0]


def create(conn: sqlite3.Connection, user_id: str, review: dict[str, Any]) -> dict[str, Any]:
    conn.execute(
        "INSERT INTO interview_reviews"
        "(id, user_id, application_id, file_name, uploaded_at, status, polls, duration_sec, "
        "transcript, overall_summary, dimensions_json, improvement_advice, error) "
        "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (review["id"], user_id, review["applicationId"], review.get("fileName", "audio"),
         review.get("uploadedAt", 0), review.get("status", "transcribing"), review.get("polls", 0),
         review.get("durationSec"), review.get("transcript", ""), review.get("overallSummary", ""),
         json.dumps(review.get("dimensions", [])), review.get("improvementAdvice", ""), review.get("error")),
    )
    return review


def save(conn: sqlite3.Connection, review: dict[str, Any]) -> None:
    """Update a review's mutable fields (identified by id)."""
    conn.execute(
        "UPDATE interview_reviews SET status = ?, polls = ?, duration_sec = ?, transcript = ?, "
        "overall_summary = ?, dimensions_json = ?, improvement_advice = ?, error = ? WHERE id = ?",
        (review.get("status", "transcribing"), review.get("polls", 0), review.get("durationSec"),
         review.get("transcript", ""), review.get("overallSummary", ""),
         json.dumps(review.get("dimensions", [])), review.get("improvementAdvice", ""),
         review.get("error"), review["id"]),
    )


def delete(conn: sqlite3.Connection, user_id: str, app_id: str, review_id: str) -> bool:
    cur = conn.execute(
        "DELETE FROM interview_reviews WHERE user_id = ? AND application_id = ? AND id = ?",
        (user_id, app_id, review_id),
    )
    return cur.rowcount > 0
