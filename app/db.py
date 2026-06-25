"""Database access for the repository layer (P0 sample slice).

This is the seam that replaces the in-memory mirror in ``app.services.store``.
Repositories take a ``sqlite3.Connection`` and run direct, per-row SQL against
the normalized schema -- no whole-bucket serialization, no full-table rewrites.

During the incremental migration the connection is *borrowed* from the legacy
``store`` singleton so both layers see the same uncommitted rows and share the
same ``PRAGMA foreign_keys = ON``. End state: this module owns the connection
(or a per-request pool) and ``app.services.store`` is deleted.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator


def get_connection() -> sqlite3.Connection:
    """Return the process-wide SQLite connection."""
    # Imported lazily to avoid import cycles and to make the temporary bridge to
    # the legacy store explicit and easy to delete later.
    from app.services.store import store

    return store._conn


def get_conn() -> Iterator[sqlite3.Connection]:
    """FastAPI dependency: yield the connection, commit on success, roll back on error.

    Usage::

        def endpoint(conn: sqlite3.Connection = Depends(get_conn)): ...
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
