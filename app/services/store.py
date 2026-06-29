from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings


@dataclass
class UserRecord:
    id: str
    email: str
    name: str
    password_hash: str
    created_at: int


class Store:
    """Owns the SQLite connection and schema.

    Every domain -- per-user data and the read-only catalogs alike -- is accessed
    through ``app/repositories/*`` now; nothing is mirrored in memory. This class
    just opens the connection, ensures the schema, and offers a test-reset helper.
    (Transitional: ``app/db.py`` borrows this connection; the end state folds this
    into ``app/db.py`` and deletes this module.)
    """

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_database_file()
        conn = sqlite3.connect(self.database_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        self._conn = conn
        self._ensure_schema()

    def _ensure_database_file(self) -> None:
        if self.database_path.exists():
            return
        initial_path = self.database_path.with_name("career_helper_initial.sqlite3")
        if initial_path.exists() and initial_path.resolve() != self.database_path.resolve():
            shutil.copyfile(initial_path, self.database_path)

    def _ensure_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS skills (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL UNIQUE COLLATE NOCASE,
              normalized_name TEXT NOT NULL UNIQUE,
              category TEXT,
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS skill_aliases (
              alias TEXT PRIMARY KEY COLLATE NOCASE,
              normalized_alias TEXT NOT NULL UNIQUE,
              skill_id TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
              source TEXT NOT NULL DEFAULT 'manual',
              created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_skill_aliases_skill_id ON skill_aliases(skill_id);

            CREATE TABLE IF NOT EXISTS users (
              id TEXT PRIMARY KEY,
              email TEXT NOT NULL UNIQUE COLLATE NOCASE,
              name TEXT NOT NULL,
              password_hash TEXT NOT NULL,
              created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS refresh_tokens (
              jti TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              created_at INTEGER NOT NULL DEFAULT 0,
              expires_at INTEGER,
              revoked_at INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);
            CREATE TABLE IF NOT EXISTS user_settings (
              user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
              notifications_enabled INTEGER NOT NULL DEFAULT 1,
              updated_at INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS profiles (
              user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
              name TEXT NOT NULL,
              updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS profile_education (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id TEXT NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
              sort_order INTEGER NOT NULL,
              degree TEXT NOT NULL DEFAULT '',
              school TEXT NOT NULL DEFAULT '',
              major TEXT NOT NULL DEFAULT '',
              grade REAL,
              start TEXT NOT NULL DEFAULT '',
              end TEXT
            );
            CREATE TABLE IF NOT EXISTS profile_internships (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id TEXT NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
              sort_order INTEGER NOT NULL,
              title TEXT NOT NULL DEFAULT '',
              company TEXT NOT NULL DEFAULT '',
              start TEXT NOT NULL DEFAULT '',
              end TEXT,
              description TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS profile_projects (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id TEXT NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
              sort_order INTEGER NOT NULL,
              title TEXT NOT NULL DEFAULT '',
              start TEXT NOT NULL DEFAULT '',
              end TEXT,
              description TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS profile_skills (
              user_id TEXT NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
              raw_text TEXT NOT NULL,
              normalized_text TEXT NOT NULL,
              skill_id TEXT REFERENCES skills(id) ON DELETE SET NULL,
              match_confidence REAL NOT NULL DEFAULT 0.0,
              source TEXT NOT NULL DEFAULT 'user',
              sort_order INTEGER NOT NULL,
              PRIMARY KEY (user_id, normalized_text)
            );
            CREATE TABLE IF NOT EXISTS profile_coursework (
              user_id TEXT NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
              course TEXT NOT NULL,
              sort_order INTEGER NOT NULL,
              PRIMARY KEY (user_id, course)
            );

            CREATE TABLE IF NOT EXISTS cv_extract_tasks (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              file_name TEXT NOT NULL DEFAULT 'cv',
              status TEXT NOT NULL DEFAULT 'processing',
              stage TEXT NOT NULL DEFAULT 'parsing',
              draft_json TEXT,
              polls INTEGER NOT NULL DEFAULT 0,
              error TEXT,
              created_at INTEGER NOT NULL DEFAULT 0,
              updated_at INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS onboarding_chat_sessions (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
              status TEXT NOT NULL,
              question TEXT,
              question_index INTEGER NOT NULL,
              total_questions INTEGER NOT NULL,
              answers_json TEXT NOT NULL DEFAULT '{}',
              draft_json TEXT,
              created_at INTEGER NOT NULL DEFAULT 0,
              updated_at INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS onboarding_chat_turns (
              id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL REFERENCES onboarding_chat_sessions(id) ON DELETE CASCADE,
              role TEXT NOT NULL,
              text TEXT NOT NULL,
              timestamp INTEGER NOT NULL,
              sort_order INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS catalog_goals (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              description TEXT NOT NULL,
              color TEXT NOT NULL,
              default_status TEXT NOT NULL,
              sort_order INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS catalog_goal_match_signals (
              catalog_goal_id TEXT NOT NULL REFERENCES catalog_goals(id) ON DELETE CASCADE,
              signal TEXT NOT NULL,
              sort_order INTEGER NOT NULL,
              PRIMARY KEY (catalog_goal_id, signal)
            );
            CREATE TABLE IF NOT EXISTS catalog_core_skills (
              id TEXT PRIMARY KEY,
              catalog_goal_id TEXT NOT NULL REFERENCES catalog_goals(id) ON DELETE CASCADE,
              name TEXT NOT NULL,
              description TEXT NOT NULL,
              default_status TEXT NOT NULL,
              sort_order INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS catalog_skill_steps (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              skill_id TEXT NOT NULL REFERENCES catalog_core_skills(id) ON DELETE CASCADE,
              step_index INTEGER NOT NULL,
              text TEXT NOT NULL,
              UNIQUE (skill_id, step_index)
            );
            CREATE TABLE IF NOT EXISTS catalog_skill_resources (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              skill_id TEXT NOT NULL REFERENCES catalog_core_skills(id) ON DELETE CASCADE,
              resource_index INTEGER NOT NULL,
              title TEXT NOT NULL,
              type TEXT NOT NULL,
              url TEXT NOT NULL,
              UNIQUE (skill_id, resource_index)
            );
            CREATE TABLE IF NOT EXISTS catalog_skill_job_keywords (
              core_skill_id TEXT NOT NULL REFERENCES catalog_core_skills(id) ON DELETE CASCADE,
              skill_id TEXT NOT NULL REFERENCES skills(id),
              sort_order INTEGER NOT NULL,
              PRIMARY KEY (core_skill_id, skill_id)
            );

            CREATE TABLE IF NOT EXISTS jobs (
              id TEXT PRIMARY KEY,
              catalog_goal_id TEXT NOT NULL REFERENCES catalog_goals(id),
              title TEXT NOT NULL,
              company TEXT NOT NULL,
              company_tagline TEXT,
              location TEXT NOT NULL,
              type TEXT NOT NULL,
              salary TEXT NOT NULL,
              posted TEXT NOT NULL,
              partner INTEGER NOT NULL,
              exclusive INTEGER NOT NULL,
              application_url TEXT,
              description TEXT
            );
            CREATE TABLE IF NOT EXISTS job_skills (
              job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
              skill_id TEXT NOT NULL REFERENCES skills(id),
              sort_order INTEGER NOT NULL,
              PRIMARY KEY (job_id, skill_id)
            );

            CREATE TABLE IF NOT EXISTS alumni (
              id TEXT PRIMARY KEY,
              first_name TEXT NOT NULL,
              last_initial TEXT NOT NULL,
              headline TEXT,
              bio TEXT NOT NULL,
              response_time TEXT NOT NULL,
              availability TEXT NOT NULL,
              avatar_gradient TEXT NOT NULL,
              linkedin_url TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS alumni_education (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              alumni_id TEXT NOT NULL REFERENCES alumni(id) ON DELETE CASCADE,
              sort_order INTEGER NOT NULL,
              degree TEXT NOT NULL DEFAULT '',
              school TEXT NOT NULL DEFAULT '',
              major TEXT NOT NULL DEFAULT '',
              start TEXT NOT NULL DEFAULT '',
              end TEXT,
              graduation_year INTEGER
            );
            CREATE TABLE IF NOT EXISTS alumni_work_experiences (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              alumni_id TEXT NOT NULL REFERENCES alumni(id) ON DELETE CASCADE,
              sort_order INTEGER NOT NULL,
              title TEXT NOT NULL,
              company TEXT NOT NULL,
              industry TEXT,
              start TEXT NOT NULL DEFAULT '',
              end TEXT,
              description TEXT NOT NULL DEFAULT '',
              is_current INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS alumni_expertise (
              alumni_id TEXT NOT NULL REFERENCES alumni(id) ON DELETE CASCADE,
              skill_id TEXT NOT NULL REFERENCES skills(id),
              display_label TEXT,
              sort_order INTEGER NOT NULL,
              PRIMARY KEY (alumni_id, skill_id)
            );
            CREATE TABLE IF NOT EXISTS alumni_topics (
              alumni_id TEXT NOT NULL REFERENCES alumni(id) ON DELETE CASCADE,
              topic TEXT NOT NULL,
              sort_order INTEGER NOT NULL,
              PRIMARY KEY (alumni_id, topic)
            );
            CREATE TABLE IF NOT EXISTS alumni_goal_alignment (
              alumni_id TEXT NOT NULL REFERENCES alumni(id) ON DELETE CASCADE,
              catalog_goal_id TEXT NOT NULL REFERENCES catalog_goals(id),
              PRIMARY KEY (alumni_id, catalog_goal_id)
            );

            CREATE TABLE IF NOT EXISTS user_goals (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              catalog_id TEXT NOT NULL REFERENCES catalog_goals(id),
              title TEXT NOT NULL,
              description TEXT NOT NULL,
              color TEXT NOT NULL,
              status TEXT NOT NULL,
              progress INTEGER NOT NULL DEFAULT 0,
              last_updated TEXT NOT NULL,
              created_at INTEGER NOT NULL,
              sort_order INTEGER NOT NULL,
              UNIQUE (user_id, catalog_id)
            );
            CREATE TABLE IF NOT EXISTS user_goal_confidence (
              goal_id TEXT NOT NULL REFERENCES user_goals(id) ON DELETE CASCADE,
              skill_id TEXT NOT NULL,
              score INTEGER NOT NULL,
              PRIMARY KEY (goal_id, skill_id)
            );
            CREATE TABLE IF NOT EXISTS goal_tracking (
              goal_id TEXT PRIMARY KEY REFERENCES user_goals(id) ON DELETE CASCADE,
              week_started_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS goal_tracking_modules (
              goal_id TEXT NOT NULL REFERENCES goal_tracking(goal_id) ON DELETE CASCADE,
              skill_id TEXT NOT NULL,
              steps_completed_since_rerate INTEGER NOT NULL DEFAULT 0,
              rerate_dismissed INTEGER NOT NULL DEFAULT 0,
              PRIMARY KEY (goal_id, skill_id)
            );
            CREATE TABLE IF NOT EXISTS goal_tracking_completed_steps (
              goal_id TEXT NOT NULL,
              skill_id TEXT NOT NULL,
              step_index INTEGER NOT NULL,
              PRIMARY KEY (goal_id, skill_id, step_index),
              FOREIGN KEY (goal_id, skill_id) REFERENCES goal_tracking_modules(goal_id, skill_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS goal_tracking_consumed_resources (
              goal_id TEXT NOT NULL,
              skill_id TEXT NOT NULL,
              resource_index INTEGER NOT NULL,
              PRIMARY KEY (goal_id, skill_id, resource_index),
              FOREIGN KEY (goal_id, skill_id) REFERENCES goal_tracking_modules(goal_id, skill_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS goal_tracking_week_focus (
              goal_id TEXT NOT NULL REFERENCES goal_tracking(goal_id) ON DELETE CASCADE,
              focus TEXT NOT NULL,
              sort_order INTEGER NOT NULL,
              PRIMARY KEY (goal_id, focus)
            );

            CREATE TABLE IF NOT EXISTS saved_jobs (
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              goal_id TEXT NOT NULL REFERENCES user_goals(id) ON DELETE CASCADE,
              job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
              saved_at INTEGER NOT NULL DEFAULT 0,
              PRIMARY KEY (user_id, goal_id, job_id)
            );
            CREATE TABLE IF NOT EXISTS applications (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              kind TEXT NOT NULL,
              goal_id TEXT NOT NULL REFERENCES user_goals(id) ON DELETE CASCADE,
              job_id TEXT NOT NULL REFERENCES jobs(id),
              title TEXT NOT NULL,
              company TEXT NOT NULL,
              submitted_at INTEGER NOT NULL,
              partner_status TEXT,
              manual_status TEXT,
              cv_text TEXT,
              UNIQUE (user_id, job_id)
            );
            CREATE TABLE IF NOT EXISTS interview_reviews (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              application_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
              file_name TEXT NOT NULL,
              uploaded_at INTEGER NOT NULL,
              status TEXT NOT NULL,
              polls INTEGER NOT NULL DEFAULT 0,
              duration_sec INTEGER,
              transcript TEXT NOT NULL DEFAULT '',
              overall_summary TEXT NOT NULL DEFAULT '',
              dimensions_json TEXT NOT NULL DEFAULT '[]',
              improvement_advice TEXT NOT NULL DEFAULT '',
              error TEXT
            );
            CREATE TABLE IF NOT EXISTS mock_interview_sessions (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              application_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
              job_title TEXT NOT NULL,
              company TEXT NOT NULL,
              goal_title TEXT,
              skills_json TEXT NOT NULL DEFAULT '[]',
              status TEXT NOT NULL,
              started_at INTEGER NOT NULL,
              completed_at INTEGER,
              duration_sec INTEGER,
              transcript TEXT NOT NULL DEFAULT '',
              overall_summary TEXT NOT NULL DEFAULT '',
              dimensions_json TEXT NOT NULL DEFAULT '[]',
              improvement_advice TEXT NOT NULL DEFAULT '',
              questions_json TEXT NOT NULL DEFAULT '[]',
              current_index INTEGER NOT NULL DEFAULT 0,
              error TEXT
            );
            CREATE TABLE IF NOT EXISTS mock_interview_turns (
              id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL REFERENCES mock_interview_sessions(id) ON DELETE CASCADE,
              role TEXT NOT NULL,
              text TEXT NOT NULL,
              timestamp INTEGER NOT NULL,
              sort_order INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tts_cache (
              turn_id TEXT PRIMARY KEY,
              audio BLOB NOT NULL,
              created_at INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS meetings (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              alumni_id TEXT NOT NULL REFERENCES alumni(id),
              topic TEXT NOT NULL,
              message TEXT NOT NULL,
              submitted_at INTEGER NOT NULL,
              status TEXT NOT NULL,
              completed_at INTEGER
            );
            CREATE UNIQUE INDEX IF NOT EXISTS ux_meetings_one_pending_per_alumni
              ON meetings(user_id, alumni_id) WHERE status = 'pending';
            CREATE TABLE IF NOT EXISTS meeting_preferred_times (
              meeting_id TEXT NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
              preferred_time TEXT NOT NULL,
              sort_order INTEGER NOT NULL,
              PRIMARY KEY (meeting_id, preferred_time)
            );
            CREATE TABLE IF NOT EXISTS notifications (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              type TEXT NOT NULL,
              severity TEXT NOT NULL,
              title TEXT NOT NULL,
              body TEXT NOT NULL,
              link TEXT,
              created_at INTEGER NOT NULL,
              read INTEGER NOT NULL DEFAULT 0,
              dedup_key TEXT,
              UNIQUE (user_id, dedup_key)
            );
            """
        )
        self._conn.commit()

    def reset_all(self, *, preserve_catalogs: bool = True) -> None:
        """Wipe all per-user data (used to isolate tests).

        ``users`` is the root of the FK graph, so deleting it cascades every
        per-user domain; ``tts_cache`` has no FK and is cleared explicitly. The
        read-only catalogs are left intact (``preserve_catalogs`` is always True
        in practice).
        """
        self._conn.execute("DELETE FROM users")
        self._conn.execute("DELETE FROM tts_cache")
        self._conn.commit()


store = Store(settings.local_database_path)

# Catalog table -> human label, for the startup presence check.
_CATALOG_TABLES = {"catalog_goals": "goal catalog", "jobs": "jobs", "alumni": "alumni"}


def seed_catalogs() -> None:
    """Verify the read-only catalogs are present in the local SQLite database."""
    missing = [
        label
        for table, label in _CATALOG_TABLES.items()
        if not store._conn.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone()
    ]
    if missing:
        raise RuntimeError(f"Missing catalog data in SQLite database: {', '.join(missing)}")
