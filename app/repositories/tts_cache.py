"""TTS audio cache repository.

``tts_cache`` keys synthesized audio by mock-interview turn id. There is no FK to
the turns table, so audio is purged explicitly (per user) the way the legacy
``_purge_tts_for`` did.
"""

from __future__ import annotations

import sqlite3


def get(conn: sqlite3.Connection, turn_id: str) -> bytes | None:
    row = conn.execute("SELECT audio FROM tts_cache WHERE turn_id = ?", (turn_id,)).fetchone()
    return row["audio"] if row else None


def put(conn: sqlite3.Connection, turn_id: str, audio: bytes) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO tts_cache(turn_id, audio, created_at) VALUES(?, ?, 0)",
        (turn_id, audio),
    )


def purge_for_user(conn: sqlite3.Connection, user_id: str) -> None:
    """Drop cached audio for all of the user's mock-interview turns."""
    conn.execute(
        "DELETE FROM tts_cache WHERE turn_id IN ("
        "  SELECT t.id FROM mock_interview_turns t "
        "  JOIN mock_interview_sessions s ON s.id = t.session_id "
        "  WHERE s.user_id = ?"
        ")",
        (user_id,),
    )
