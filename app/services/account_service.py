"""Account-level orchestration across repositories (SET-07 / SET-08).

These ran on the store mirror before; now they compose repository calls on a
caller-supplied connection. They do NOT commit -- the surrounding ``get_conn``
dependency owns the transaction.
"""

from __future__ import annotations

import sqlite3

from app.repositories import auth as auth_repo
from app.repositories import goals as goals_repo
from app.repositories import meetings as meetings_repo
from app.repositories import notifications as notifications_repo
from app.repositories import onboarding_chats as onboarding_chats_repo
from app.repositories import profiles as profiles_repo
from app.repositories import tts_cache as tts_cache_repo


def reset_user_data(conn: sqlite3.Connection, user_id: str) -> None:
    """Clear demo data but keep the account (use-case SET-07)."""
    # Purge cached TTS audio before the goal cascade removes the mock turns it is
    # keyed by (tts_cache has no FK to cascade through).
    tts_cache_repo.purge_for_user(conn, user_id)
    meetings_repo.delete_for_user(conn, user_id)
    notifications_repo.delete_for_user(conn, user_id)
    onboarding_chats_repo.delete(conn, user_id)
    profiles_repo.delete(conn, user_id)
    # Deleting the user's goals cascades to tracking, saved_jobs, applications,
    # interview reviews and mock sessions.
    goals_repo.delete_all_for_user(conn, user_id)


def delete_account(conn: sqlite3.Connection, user_id: str) -> None:
    """Remove the account and all of its data (use-case SET-08)."""
    # Purge TTS audio before the user cascade drops the mock turns it keys on.
    tts_cache_repo.purge_for_user(conn, user_id)
    # Dropping the user row cascades every per-user domain via FK.
    auth_repo.delete_user(conn, user_id)
