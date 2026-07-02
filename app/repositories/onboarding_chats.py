"""Onboarding chat repository (parent + child aggregate).

One ``onboarding_chat_sessions`` row per user with its ordered
``onboarding_chat_turns`` children. ``save`` replaces just that user's session
(the child turns cascade) instead of the legacy global "DELETE every session and
turn, reinsert all" rewrite.

Unlike the other repositories, the session working-dict here is kept in the
camelCase shape the router mutates throughout its onboarding flow (and which the
``OnboardingChatSession`` schema already uses). The repo maps that dict to/from
the snake_case columns, so the snake/camel translation still lives at this
boundary -- it just isn't worth rewriting the (CI-untested) real-AI advance logic
to flip the in-memory dict's casing.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any


def _from_json(value: str | None, default: Any) -> Any:
    return json.loads(value) if value not in (None, "") else default


def get(conn: sqlite3.Connection, user_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM onboarding_chat_sessions WHERE user_id = ?", (user_id,)
    ).fetchone()
    if row is None:
        return None
    turns = [
        {"id": t["id"], "role": t["role"], "text": t["text"], "timestamp": t["timestamp"]}
        for t in conn.execute(
            "SELECT * FROM onboarding_chat_turns WHERE session_id = ? ORDER BY sort_order",
            (row["id"],),
        )
    ]
    return {
        "id": row["id"],
        "status": row["status"],
        "question": row["question"],
        "questionIndex": row["question_index"],
        "totalQuestions": row["total_questions"],
        "turns": turns,
        "answers": _from_json(row["answers_json"], {}),
        "draft": _from_json(row["draft_json"], None),
    }


def save(conn: sqlite3.Connection, user_id: str, session: dict[str, Any]) -> None:
    """Persist a user's session and its turns (one session per user).

    Replaces the user's existing row -- the turns cascade via FK -- then inserts
    the new session and its ordered turns. Scoped to this user, not the table.
    """
    conn.execute("DELETE FROM onboarding_chat_sessions WHERE user_id = ?", (user_id,))
    conn.execute(
        "INSERT INTO onboarding_chat_sessions"
        "(id, user_id, status, question, question_index, total_questions, answers_json, draft_json) "
        "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
        (
            session["id"],
            user_id,
            session["status"],
            session.get("question"),
            session.get("questionIndex", 0),
            session.get("totalQuestions", 0),
            json.dumps(session.get("answers", {})),
            json.dumps(session["draft"]) if session.get("draft") is not None else None,
        ),
    )
    for idx, turn in enumerate(session.get("turns", [])):
        conn.execute(
            "INSERT INTO onboarding_chat_turns(id, session_id, role, text, timestamp, sort_order) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            (turn["id"], session["id"], turn["role"], turn["text"], turn["timestamp"], idx),
        )


def delete(conn: sqlite3.Connection, user_id: str) -> bool:
    """Discard a user's onboarding session (turns cascade). True if one existed."""
    cur = conn.execute("DELETE FROM onboarding_chat_sessions WHERE user_id = ?", (user_id,))
    return cur.rowcount > 0
