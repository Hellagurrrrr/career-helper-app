"""Auth repository: users + refresh tokens.

Replaces the last per-user state in the in-memory store mirror. ``users`` is the
root of the FK graph, so ``delete_user`` cascades to every per-user domain. The
former ``email_index`` mirror was just a derived lookup over users -- it is gone,
replaced by ``get_user_by_email`` / ``email_exists`` (the ``users.email`` column
is ``UNIQUE COLLATE NOCASE``).

Refresh tokens follow the legacy semantics: a row present (and not revoked) means
valid; revoking deletes the row.
"""

from __future__ import annotations

import sqlite3

from app.models import UserRecord


def _row_to_user(row: sqlite3.Row) -> UserRecord:
    return UserRecord(
        id=row["id"],
        email=row["email"],
        name=row["name"],
        password_hash=row["password_hash"],
        created_at=row["created_at"],
    )


# ----- users -----
def get_user(conn: sqlite3.Connection, user_id: str) -> UserRecord | None:
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _row_to_user(row) if row else None


def get_user_by_email(conn: sqlite3.Connection, email: str) -> UserRecord | None:
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return _row_to_user(row) if row else None


def email_exists(conn: sqlite3.Connection, email: str) -> bool:
    return (
        conn.execute("SELECT 1 FROM users WHERE email = ? LIMIT 1", (email,)).fetchone() is not None
    )


def create_user(conn: sqlite3.Connection, user: UserRecord) -> UserRecord:
    conn.execute(
        "INSERT INTO users(id, email, name, password_hash, created_at) VALUES(?, ?, ?, ?, ?)",
        (user.id, user.email, user.name, user.password_hash, user.created_at),
    )
    return user


def update_password(conn: sqlite3.Connection, user_id: str, password_hash: str) -> None:
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))


def delete_user(conn: sqlite3.Connection, user_id: str) -> None:
    """Delete the account. Every per-user domain cascades via FK."""
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


# ----- refresh tokens -----
def add_refresh_token(conn: sqlite3.Connection, jti: str, user_id: str) -> None:
    conn.execute(
        "INSERT INTO refresh_tokens(jti, user_id, created_at) VALUES(?, ?, 0)", (jti, user_id)
    )


def refresh_token_user(conn: sqlite3.Connection, jti: str) -> str | None:
    """Return the owning user_id of a live refresh token, or None if revoked/missing."""
    row = conn.execute(
        "SELECT user_id FROM refresh_tokens WHERE jti = ? AND revoked_at IS NULL", (jti,)
    ).fetchone()
    return row["user_id"] if row else None


def revoke_refresh_token(conn: sqlite3.Connection, jti: str) -> None:
    conn.execute("DELETE FROM refresh_tokens WHERE jti = ?", (jti,))


def revoke_all_refresh_tokens(conn: sqlite3.Connection, user_id: str) -> None:
    conn.execute("DELETE FROM refresh_tokens WHERE user_id = ?", (user_id,))
