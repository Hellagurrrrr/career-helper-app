"""SQLite connection + schema for the repository layer.

Owns the single process-wide connection. Repositories take a
``sqlite3.Connection`` and run direct, per-row SQL against the normalized schema
(defined in ``app/data/schema.sql``) -- no in-memory mirror, no full-table
rewrites. ``get_conn`` is the FastAPI dependency that commits on success and
rolls back on error.
"""

from __future__ import annotations

import shutil
import sqlite3
import threading
from collections.abc import Iterator
from pathlib import Path

from app.core.config import settings

_SCHEMA_PATH = Path(__file__).resolve().parent / "data" / "schema.sql"
# Catalog table -> human label, for the startup presence check.
_CATALOG_TABLES = {"catalog_goals": "goal catalog", "jobs": "jobs", "alumni": "alumni"}


def _ensure_database_file(database_path: Path) -> None:
    """Seed a fresh database file from the shipped catalog snapshot, if present."""
    if database_path.exists():
        return
    initial = database_path.with_name("career_helper_initial.sqlite3")
    if initial.exists() and initial.resolve() != database_path.resolve():
        shutil.copyfile(initial, database_path)


def _create_connection() -> sqlite3.Connection:
    database_path = Path(settings.local_database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    _ensure_database_file(database_path)
    conn = sqlite3.connect(database_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()
    return conn


_connection: sqlite3.Connection | None = None
_connection_lock = threading.Lock()


def get_connection() -> sqlite3.Connection:
    """Return the process-wide SQLite connection, opening it on first use.

    Initialization is lazy (not an import-time side effect) so importing this
    module never touches the filesystem or runs the schema. The lock makes the
    one-time open safe under the thread pool ``check_same_thread=False`` allows.
    """
    global _connection
    if _connection is None:
        with _connection_lock:
            if _connection is None:
                _connection = _create_connection()
    return _connection


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


def reset_all() -> None:
    """Wipe all per-user data (test isolation).

    ``users`` is the root of the FK graph, so deleting it cascades every per-user
    domain; ``tts_cache`` has no FK and is cleared explicitly. The read-only
    catalogs are left intact.
    """
    conn = get_connection()
    conn.execute("DELETE FROM users")
    conn.execute("DELETE FROM tts_cache")
    conn.commit()


def seed_catalogs() -> None:
    """Verify the read-only catalogs are present in the local SQLite database."""
    conn = get_connection()
    missing = [
        label
        for table, label in _CATALOG_TABLES.items()
        if not conn.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone()
    ]
    if missing:
        raise RuntimeError(f"Missing catalog data in SQLite database: {', '.join(missing)}")
