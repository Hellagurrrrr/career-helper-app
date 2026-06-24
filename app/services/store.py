from __future__ import annotations

import base64
import json
import re
import shutil
import sqlite3
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.core.config import settings


@dataclass
class UserRecord:
    id: str
    email: str
    name: str
    password_hash: str
    created_at: int


StoreValue = Any
SaveCallback = Callable[[], None]


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _from_json(value: str | None, default: Any) -> Any:
    if value in (None, ""):
        return default
    return json.loads(value)


def _snake_to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _row_to_camel(row: sqlite3.Row) -> dict[str, Any]:
    return {_snake_to_camel(k): row[k] for k in row.keys()}


def _normalize_skill_text(raw: str) -> str:
    text = raw.strip().lower()
    text = re.sub(r"[._/+-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if text.endswith(" js"):
        text = text[:-3].strip()
    return text


def _skill_id_for(name: str) -> str:
    normalized = _normalize_skill_text(name)
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return f"skill-{slug or 'unknown'}"


def _encode_legacy(value: StoreValue) -> StoreValue:
    if isinstance(value, UserRecord):
        return {"__type__": "UserRecord", "value": asdict(value)}
    if isinstance(value, bytes):
        return {"__type__": "bytes", "value": base64.b64encode(value).decode("ascii")}
    if isinstance(value, (PersistentSet, set)):
        return {"__type__": "set", "value": [_encode_legacy(v) for v in value]}
    if isinstance(value, (PersistentDict, dict)):
        return {str(k): _encode_legacy(v) for k, v in value.items()}
    if isinstance(value, (PersistentList, list)):
        return [_encode_legacy(v) for v in value]
    return value


def _decode_legacy(value: StoreValue) -> StoreValue:
    if isinstance(value, dict) and value.get("__type__") == "UserRecord":
        return UserRecord(**value["value"])
    if isinstance(value, dict) and value.get("__type__") == "bytes":
        return base64.b64decode(value["value"].encode("ascii"))
    if isinstance(value, dict) and value.get("__type__") == "set":
        return set(_decode_legacy(v) for v in value["value"])
    if isinstance(value, dict):
        return {k: _decode_legacy(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_decode_legacy(v) for v in value]
    return value


def _wrap(value: StoreValue, save: SaveCallback) -> StoreValue:
    if isinstance(value, PersistentDict | PersistentList | PersistentSet):
        value._set_save(save)
        return value
    if isinstance(value, dict):
        return PersistentDict(value, save)
    if isinstance(value, list):
        return PersistentList(value, save)
    if isinstance(value, set):
        return PersistentSet(value, save)
    return value


class PersistentDict(dict):
    def __init__(self, values: Mapping[str, StoreValue] | None = None, save: SaveCallback | None = None):
        super().__init__()
        self._save = save or (lambda: None)
        for key, value in (values or {}).items():
            dict.__setitem__(self, key, _wrap(value, self._save))

    def _set_save(self, save: SaveCallback) -> None:
        self._save = save
        for value in self.values():
            if isinstance(value, PersistentDict | PersistentList | PersistentSet):
                value._set_save(save)

    def __setitem__(self, key: str, value: StoreValue) -> None:
        dict.__setitem__(self, key, _wrap(value, self._save))
        self._save()

    def __delitem__(self, key: str) -> None:
        dict.__delitem__(self, key)
        self._save()

    def clear(self) -> None:
        dict.clear(self)
        self._save()

    def pop(self, key: str, default: StoreValue = None) -> StoreValue:
        value = dict.pop(self, key, default)
        self._save()
        return value

    def popitem(self) -> tuple[str, StoreValue]:
        value = dict.popitem(self)
        self._save()
        return value

    def setdefault(self, key: str, default: StoreValue = None) -> StoreValue:
        if key not in self:
            self[key] = default
        return dict.__getitem__(self, key)

    def update(self, *args: Any, **kwargs: StoreValue) -> None:
        updates = dict(*args, **kwargs)
        for key, value in updates.items():
            dict.__setitem__(self, key, _wrap(value, self._save))
        self._save()


class PersistentList(list):
    def __init__(self, values: Iterable[StoreValue] | None = None, save: SaveCallback | None = None):
        self._save = save or (lambda: None)
        super().__init__(_wrap(value, self._save) for value in (values or []))

    def _set_save(self, save: SaveCallback) -> None:
        self._save = save
        for value in self:
            if isinstance(value, PersistentDict | PersistentList | PersistentSet):
                value._set_save(save)

    def __setitem__(self, key: int | slice, value: StoreValue) -> None:
        if isinstance(key, slice):
            list.__setitem__(self, key, [_wrap(v, self._save) for v in value])
        else:
            list.__setitem__(self, key, _wrap(value, self._save))
        self._save()

    def __delitem__(self, key: int | slice) -> None:
        list.__delitem__(self, key)
        self._save()

    def append(self, value: StoreValue) -> None:
        list.append(self, _wrap(value, self._save))
        self._save()

    def clear(self) -> None:
        list.clear(self)
        self._save()

    def extend(self, values: Iterable[StoreValue]) -> None:
        list.extend(self, [_wrap(value, self._save) for value in values])
        self._save()

    def insert(self, index: int, value: StoreValue) -> None:
        list.insert(self, index, _wrap(value, self._save))
        self._save()

    def pop(self, index: int = -1) -> StoreValue:
        value = list.pop(self, index)
        self._save()
        return value

    def remove(self, value: StoreValue) -> None:
        list.remove(self, value)
        self._save()


class PersistentSet(set):
    def __init__(self, values: Iterable[StoreValue] | None = None, save: SaveCallback | None = None):
        self._save = save or (lambda: None)
        super().__init__(values or [])

    def _set_save(self, save: SaveCallback) -> None:
        self._save = save

    def add(self, value: StoreValue) -> None:
        set.add(self, value)
        self._save()

    def clear(self) -> None:
        set.clear(self)
        self._save()

    def discard(self, value: StoreValue) -> None:
        set.discard(self, value)
        self._save()

    def pop(self) -> StoreValue:
        value = set.pop(self)
        self._save()
        return value

    def remove(self, value: StoreValue) -> None:
        set.remove(self, value)
        self._save()


class Store:
    """Normalized SQLite repository with a compatibility dict/list interface."""

    _catalog_buckets = ("goal_catalog", "jobs", "alumni")
    _bucket_defaults: dict[str, StoreValue] = {
        "users": {},
        "email_index": {},
        "refresh_jti": {},
        "user_settings": {},
        "profiles": {},
        "cv_tasks": {},
        "onboarding_chats": {},
        "goals": {},
        "tracking": {},
        "saved_jobs": {},
        "applications": {},
        "reviews": {},
        "mocks": {},
        "tts_cache": {},
        "meetings": {},
        "notifications": {},
        "goal_catalog": [],
        "jobs": [],
        "alumni": [],
    }

    def __init__(self, database_path: str | Path):
        object.__setattr__(self, "database_path", Path(database_path))
        object.__setattr__(self, "_loading", True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_database_file()
        conn = sqlite3.connect(self.database_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        object.__setattr__(self, "_conn", conn)
        self._ensure_schema()

        legacy = self._load_legacy_buckets() if not self._has_normalized_data() else {}
        for name, default in self._bucket_defaults.items():
            value = legacy.get(name, self._load_bucket(name, default))
            object.__setattr__(self, name, _wrap(value, lambda bucket=name: self._save_bucket(bucket)))

        object.__setattr__(self, "_loading", False)
        if legacy:
            for name in self._bucket_defaults:
                self._save_bucket(name)
            self._conn.execute("DROP TABLE IF EXISTS store_buckets")
            self._conn.commit()

    def _ensure_database_file(self) -> None:
        if self.database_path.exists():
            return

        initial_path = self.database_path.with_name("career_helper_initial.sqlite3")
        if initial_path.exists() and initial_path.resolve() != self.database_path.resolve():
            shutil.copyfile(initial_path, self.database_path)

    def __setattr__(self, name: str, value: StoreValue) -> None:
        if name in self._bucket_defaults:
            object.__setattr__(self, name, _wrap(value, lambda bucket=name: self._save_bucket(bucket)))
            if not getattr(self, "_loading", False):
                self._save_bucket(name)
            return
        object.__setattr__(self, name, value)

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

    def _has_normalized_data(self) -> bool:
        tables = ("catalog_goals", "users", "jobs", "alumni")
        return any(self._conn.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone() for table in tables)

    def _load_legacy_buckets(self) -> dict[str, Any]:
        exists = self._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'store_buckets'"
        ).fetchone()
        if not exists:
            return {}
        rows = self._conn.execute("SELECT name, value FROM store_buckets").fetchall()
        return {row["name"]: _decode_legacy(json.loads(row["value"])) for row in rows}

    def reset_all(self, *, preserve_catalogs: bool = True) -> None:
        for name, default in self._bucket_defaults.items():
            if preserve_catalogs and name in self._catalog_buckets:
                continue
            setattr(self, name, default.copy() if isinstance(default, (dict, list, set)) else default)

    def ensure_user_buckets(self, user_id: str) -> None:
        self.user_settings.setdefault(user_id, {"notificationsEnabled": True, "updatedAt": 0})
        self.profiles.setdefault(user_id, None)
        self.onboarding_chats.setdefault(user_id, None)
        self.goals.setdefault(user_id, {})
        self.tracking.setdefault(user_id, {})
        self.saved_jobs.setdefault(user_id, {})
        self.applications.setdefault(user_id, {})
        self.reviews.setdefault(user_id, {})
        self.mocks.setdefault(user_id, {})
        self.meetings.setdefault(user_id, {})
        self.notifications.setdefault(user_id, [])

    def _load_bucket(self, name: str, default: StoreValue) -> StoreValue:
        loader = getattr(self, f"_load_{name}", None)
        if loader:
            return loader()
        return default.copy() if isinstance(default, (dict, list, set)) else default

    def _save_bucket(self, name: str) -> None:
        if self._loading:
            return
        saver = getattr(self, f"_save_{name}", None)
        if saver:
            saver(getattr(self, name))
            self._conn.commit()

    def _get_or_create_skill(self, name: str, source: str = "seed") -> str:
        display = name.strip()
        normalized = _normalize_skill_text(display)
        if not normalized:
            display = "Unknown"
            normalized = "unknown"
        row = self._conn.execute(
            "SELECT skill_id FROM skill_aliases WHERE normalized_alias = ?", (normalized,)
        ).fetchone()
        if row:
            return row["skill_id"]
        skill_id = _skill_id_for(display)
        now = 0
        self._conn.execute(
            "INSERT OR IGNORE INTO skills(id, name, normalized_name, category, created_at, updated_at) "
            "VALUES(?, ?, ?, NULL, ?, ?)",
            (skill_id, display, normalized, now, now),
        )
        self._conn.execute(
            "INSERT OR IGNORE INTO skill_aliases(alias, normalized_alias, skill_id, source, created_at) "
            "VALUES(?, ?, ?, ?, ?)",
            (display, normalized, skill_id, source, now),
        )
        return skill_id

    def _skill_name(self, skill_id: str, fallback: str = "") -> str:
        row = self._conn.execute("SELECT name FROM skills WHERE id = ?", (skill_id,)).fetchone()
        return row["name"] if row else fallback

    # ----- auth -----
    def _load_users(self) -> dict[str, UserRecord]:
        rows = self._conn.execute("SELECT * FROM users").fetchall()
        return {
            row["id"]: UserRecord(
                id=row["id"],
                email=row["email"],
                name=row["name"],
                password_hash=row["password_hash"],
                created_at=row["created_at"],
            )
            for row in rows
        }

    def _save_users(self, users: Mapping[str, UserRecord]) -> None:
        self._conn.execute("DELETE FROM users")
        for user in users.values():
            self._conn.execute(
                "INSERT INTO users(id, email, name, password_hash, created_at) VALUES(?, ?, ?, ?, ?)",
                (user.id, user.email, user.name, user.password_hash, user.created_at),
            )

    def _load_email_index(self) -> dict[str, str]:
        return {u.email.lower(): u.id for u in self._load_users().values()}

    def _save_email_index(self, _email_index: Mapping[str, str]) -> None:
        return

    def _load_refresh_jti(self) -> dict[str, str]:
        rows = self._conn.execute("SELECT jti, user_id FROM refresh_tokens WHERE revoked_at IS NULL").fetchall()
        return {row["jti"]: row["user_id"] for row in rows}

    def _save_refresh_jti(self, refresh_jti: Mapping[str, str]) -> None:
        self._conn.execute("DELETE FROM refresh_tokens")
        for jti, user_id in refresh_jti.items():
            self._conn.execute(
                "INSERT INTO refresh_tokens(jti, user_id, created_at) VALUES(?, ?, 0)",
                (jti, user_id),
            )

    def _load_user_settings(self) -> dict[str, dict[str, Any]]:
        rows = self._conn.execute("SELECT * FROM user_settings").fetchall()
        return {
            row["user_id"]: {
                "notificationsEnabled": bool(row["notifications_enabled"]),
                "updatedAt": row["updated_at"],
            }
            for row in rows
        }

    def _save_user_settings(self, user_settings: Mapping[str, dict[str, Any]]) -> None:
        self._conn.execute("DELETE FROM user_settings")
        for user_id, prefs in user_settings.items():
            self._conn.execute(
                "INSERT OR REPLACE INTO user_settings(user_id, notifications_enabled, updated_at) VALUES(?, ?, ?)",
                (
                    user_id,
                    int(bool(prefs.get("notificationsEnabled", True))),
                    prefs.get("updatedAt", 0),
                ),
            )

    def update_user_password(self, user_id: str, password_hash: str) -> None:
        user = self.users.get(user_id)
        if user is None:
            return
        user.password_hash = password_hash
        self._conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
        self._conn.commit()

    def revoke_refresh_tokens_for_user(self, user_id: str) -> None:
        for jti, uid in list(self.refresh_jti.items()):
            if uid == user_id:
                self.refresh_jti.pop(jti, None)

    # ----- profiles -----
    def _load_profiles(self) -> dict[str, dict[str, Any] | None]:
        profiles: dict[str, dict[str, Any]] = {}
        for row in self._conn.execute("SELECT * FROM profiles").fetchall():
            user_id = row["user_id"]
            profiles[user_id] = {
                "name": row["name"],
                "education": [],
                "internships": [],
                "projects": [],
                "skills": [],
                "coursework": [],
                "updatedAt": row["updated_at"],
            }
        for table, key in (
            ("profile_education", "education"),
            ("profile_internships", "internships"),
            ("profile_projects", "projects"),
        ):
            for row in self._conn.execute(f"SELECT * FROM {table} ORDER BY sort_order").fetchall():
                item = _row_to_camel(row)
                user_id = item.pop("userId")
                item.pop("id", None)
                item.pop("sortOrder", None)
                profiles[user_id][key].append(item)
        for row in self._conn.execute("SELECT * FROM profile_skills ORDER BY sort_order").fetchall():
            profiles[row["user_id"]]["skills"].append(row["raw_text"])
        for row in self._conn.execute("SELECT * FROM profile_coursework ORDER BY sort_order").fetchall():
            profiles[row["user_id"]]["coursework"].append(row["course"])
        return profiles

    def _save_profiles(self, profiles: Mapping[str, dict[str, Any] | None]) -> None:
        for table in (
            "profile_coursework", "profile_skills", "profile_projects",
            "profile_internships", "profile_education", "profiles",
        ):
            self._conn.execute(f"DELETE FROM {table}")
        for user_id, profile in profiles.items():
            if not profile:
                continue
            self._conn.execute(
                "INSERT INTO profiles(user_id, name, updated_at) VALUES(?, ?, ?)",
                (user_id, profile.get("name", ""), profile.get("updatedAt", 0)),
            )
            for idx, edu in enumerate(profile.get("education", [])):
                self._conn.execute(
                    "INSERT INTO profile_education(user_id, sort_order, degree, school, major, grade, start, end) "
                    "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                    (user_id, idx, edu.get("degree", ""), edu.get("school", ""), edu.get("major", ""),
                     edu.get("grade"), edu.get("start", ""), edu.get("end")),
                )
            for idx, intern in enumerate(profile.get("internships", [])):
                self._conn.execute(
                    "INSERT INTO profile_internships(user_id, sort_order, title, company, start, end, description) "
                    "VALUES(?, ?, ?, ?, ?, ?, ?)",
                    (user_id, idx, intern.get("title", ""), intern.get("company", ""), intern.get("start", ""),
                     intern.get("end"), intern.get("description", "")),
                )
            for idx, project in enumerate(profile.get("projects", [])):
                self._conn.execute(
                    "INSERT INTO profile_projects(user_id, sort_order, title, start, end, description) "
                    "VALUES(?, ?, ?, ?, ?, ?)",
                    (user_id, idx, project.get("title", ""), project.get("start", ""),
                     project.get("end"), project.get("description", "")),
                )
            for idx, skill in enumerate(profile.get("skills", [])):
                normalized = _normalize_skill_text(skill)
                row = self._conn.execute(
                    "SELECT skill_id FROM skill_aliases WHERE normalized_alias = ?", (normalized,)
                ).fetchone()
                skill_id = row["skill_id"] if row else None
                confidence = 1.0 if skill_id else 0.0
                self._conn.execute(
                    "INSERT OR REPLACE INTO profile_skills"
                    "(user_id, raw_text, normalized_text, skill_id, match_confidence, source, sort_order) "
                    "VALUES(?, ?, ?, ?, ?, 'user', ?)",
                    (user_id, skill, normalized, skill_id, confidence, idx),
                )
            for idx, course in enumerate(profile.get("coursework", [])):
                self._conn.execute(
                    "INSERT OR REPLACE INTO profile_coursework(user_id, course, sort_order) VALUES(?, ?, ?)",
                    (user_id, course, idx),
                )

    # ----- tasks and onboarding -----
    def _load_cv_tasks(self) -> dict[str, dict[str, Any]]:
        rows = self._conn.execute("SELECT * FROM cv_extract_tasks").fetchall()
        return {
            row["id"]: {
                "userId": row["user_id"],
                "fileName": row["file_name"],
                "status": row["status"],
                "stage": row["stage"],
                "draft": _from_json(row["draft_json"], None),
                "polls": row["polls"],
                "error": row["error"],
            }
            for row in rows
        }

    def _save_cv_tasks(self, tasks: Mapping[str, dict[str, Any]]) -> None:
        self._conn.execute("DELETE FROM cv_extract_tasks")
        for task_id, task in tasks.items():
            self._conn.execute(
                "INSERT INTO cv_extract_tasks"
                "(id, user_id, file_name, status, stage, draft_json, polls, error, created_at, updated_at) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, 0, 0)",
                (task_id, task.get("userId"), task.get("fileName", "cv"),
                 task.get("status", "processing"), task.get("stage", "parsing"),
                 _json(task.get("draft")) if task.get("draft") is not None else None,
                 task.get("polls", 0), task.get("error")),
            )

    def _load_onboarding_chats(self) -> dict[str, dict[str, Any] | None]:
        out: dict[str, dict[str, Any]] = {}
        rows = self._conn.execute("SELECT * FROM onboarding_chat_sessions").fetchall()
        for row in rows:
            out[row["user_id"]] = {
                "id": row["id"],
                "status": row["status"],
                "question": row["question"],
                "questionIndex": row["question_index"],
                "totalQuestions": row["total_questions"],
                "turns": [],
                "answers": _from_json(row["answers_json"], {}),
                "draft": _from_json(row["draft_json"], None),
            }
        for row in self._conn.execute("SELECT * FROM onboarding_chat_turns ORDER BY sort_order").fetchall():
            owner = self._conn.execute(
                "SELECT user_id FROM onboarding_chat_sessions WHERE id = ?", (row["session_id"],)
            ).fetchone()
            if owner and owner["user_id"] in out:
                out[owner["user_id"]]["turns"].append(
                    {"id": row["id"], "role": row["role"], "text": row["text"], "timestamp": row["timestamp"]}
                )
        return out

    def _save_onboarding_chats(self, chats: Mapping[str, dict[str, Any] | None]) -> None:
        self._conn.execute("DELETE FROM onboarding_chat_turns")
        self._conn.execute("DELETE FROM onboarding_chat_sessions")
        for user_id, session in chats.items():
            if not session:
                continue
            self._conn.execute(
                "INSERT INTO onboarding_chat_sessions"
                "(id, user_id, status, question, question_index, total_questions, answers_json, draft_json) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                (session["id"], user_id, session["status"], session.get("question"),
                 session.get("questionIndex", 0), session.get("totalQuestions", 0),
                 _json(session.get("answers", {})),
                 _json(session.get("draft")) if session.get("draft") is not None else None),
            )
            for idx, turn in enumerate(session.get("turns", [])):
                self._conn.execute(
                    "INSERT INTO onboarding_chat_turns(id, session_id, role, text, timestamp, sort_order) "
                    "VALUES(?, ?, ?, ?, ?, ?)",
                    (turn["id"], session["id"], turn["role"], turn["text"], turn["timestamp"], idx),
                )

    # ----- public catalogs -----
    def _load_goal_catalog(self) -> list[dict[str, Any]]:
        goals = []
        for row in self._conn.execute("SELECT * FROM catalog_goals ORDER BY sort_order, id").fetchall():
            goal = {
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "color": row["color"],
                "defaultStatus": row["default_status"],
                "matchSignals": [
                    r["signal"] for r in self._conn.execute(
                        "SELECT signal FROM catalog_goal_match_signals WHERE catalog_goal_id = ? ORDER BY sort_order",
                        (row["id"],),
                    )
                ],
                "coreSkills": [],
            }
            for skill in self._conn.execute(
                "SELECT * FROM catalog_core_skills WHERE catalog_goal_id = ? ORDER BY sort_order",
                (row["id"],),
            ).fetchall():
                core = {
                    "id": skill["id"],
                    "name": skill["name"],
                    "description": skill["description"],
                    "defaultStatus": skill["default_status"],
                    "whatToDo": [
                        r["text"] for r in self._conn.execute(
                            "SELECT text FROM catalog_skill_steps WHERE skill_id = ? ORDER BY step_index",
                            (skill["id"],),
                        )
                    ],
                    "resources": [
                        {"title": r["title"], "type": r["type"], "url": r["url"]}
                        for r in self._conn.execute(
                            "SELECT * FROM catalog_skill_resources WHERE skill_id = ? ORDER BY resource_index",
                            (skill["id"],),
                        )
                    ],
                    "jobSkillKeywords": [
                        self._skill_name(r["skill_id"])
                        for r in self._conn.execute(
                            "SELECT skill_id FROM catalog_skill_job_keywords WHERE core_skill_id = ? ORDER BY sort_order",
                            (skill["id"],),
                        )
                    ],
                }
                goal["coreSkills"].append(core)
            goals.append(goal)
        return goals

    def _save_goal_catalog(self, goals: Iterable[dict[str, Any]]) -> None:
        for table in (
            "catalog_skill_job_keywords", "catalog_skill_resources", "catalog_skill_steps",
            "catalog_core_skills", "catalog_goal_match_signals", "catalog_goals",
        ):
            self._conn.execute(f"DELETE FROM {table}")
        for idx, goal in enumerate(goals):
            self._conn.execute(
                "INSERT INTO catalog_goals(id, title, description, color, default_status, sort_order) "
                "VALUES(?, ?, ?, ?, ?, ?)",
                (goal["id"], goal["title"], goal["description"], goal["color"], goal["defaultStatus"], idx),
            )
            for sidx, signal in enumerate(goal.get("matchSignals", [])):
                self._conn.execute(
                    "INSERT INTO catalog_goal_match_signals(catalog_goal_id, signal, sort_order) VALUES(?, ?, ?)",
                    (goal["id"], signal, sidx),
                )
            for cidx, core in enumerate(goal.get("coreSkills", [])):
                self._conn.execute(
                    "INSERT INTO catalog_core_skills(id, catalog_goal_id, name, description, default_status, sort_order) "
                    "VALUES(?, ?, ?, ?, ?, ?)",
                    (core["id"], goal["id"], core["name"], core["description"], core["defaultStatus"], cidx),
                )
                for step_idx, step in enumerate(core.get("whatToDo", [])):
                    self._conn.execute(
                        "INSERT INTO catalog_skill_steps(skill_id, step_index, text) VALUES(?, ?, ?)",
                        (core["id"], step_idx, step),
                    )
                for ridx, res in enumerate(core.get("resources", [])):
                    self._conn.execute(
                        "INSERT INTO catalog_skill_resources(skill_id, resource_index, title, type, url) "
                        "VALUES(?, ?, ?, ?, ?)",
                        (core["id"], ridx, res["title"], res["type"], res["url"]),
                    )
                for kidx, keyword in enumerate(core.get("jobSkillKeywords", [])):
                    skill_id = self._get_or_create_skill(keyword)
                    self._conn.execute(
                        "INSERT OR REPLACE INTO catalog_skill_job_keywords(core_skill_id, skill_id, sort_order) "
                        "VALUES(?, ?, ?)",
                        (core["id"], skill_id, kidx),
                    )

    def _load_jobs(self) -> list[dict[str, Any]]:
        jobs = []
        for row in self._conn.execute("SELECT * FROM jobs ORDER BY id").fetchall():
            job = {
                "id": row["id"],
                "catalogGoalId": row["catalog_goal_id"],
                "title": row["title"],
                "company": row["company"],
                "companyTagline": row["company_tagline"],
                "location": row["location"],
                "type": row["type"],
                "salary": row["salary"],
                "posted": row["posted"],
                "skills": [
                    self._skill_name(r["skill_id"])
                    for r in self._conn.execute(
                        "SELECT skill_id FROM job_skills WHERE job_id = ? ORDER BY sort_order", (row["id"],)
                    )
                ],
                "partner": bool(row["partner"]),
                "exclusive": bool(row["exclusive"]),
                "applicationUrl": row["application_url"],
                "description": row["description"],
            }
            jobs.append({k: v for k, v in job.items() if v is not None})
        return jobs

    def _save_jobs(self, jobs: Iterable[dict[str, Any]]) -> None:
        self._conn.execute("DELETE FROM job_skills")
        self._conn.execute("DELETE FROM jobs")
        for job in jobs:
            self._conn.execute(
                "INSERT INTO jobs(id, catalog_goal_id, title, company, company_tagline, location, type, salary, "
                "posted, partner, exclusive, application_url, description) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (job["id"], job["catalogGoalId"], job["title"], job["company"], job.get("companyTagline"),
                 job.get("location", ""), job.get("type", ""), job.get("salary", ""), job.get("posted", ""),
                 int(bool(job.get("partner", False))), int(bool(job.get("exclusive", False))),
                 job.get("applicationUrl"), job.get("description")),
            )
            for idx, skill in enumerate(job.get("skills", [])):
                skill_id = self._get_or_create_skill(skill)
                self._conn.execute(
                    "INSERT OR REPLACE INTO job_skills(job_id, skill_id, sort_order) VALUES(?, ?, ?)",
                    (job["id"], skill_id, idx),
                )

    def _load_alumni(self) -> list[dict[str, Any]]:
        alumni = []
        for row in self._conn.execute("SELECT * FROM alumni ORDER BY id").fetchall():
            work = self._conn.execute(
                "SELECT * FROM alumni_work_experiences WHERE alumni_id = ? ORDER BY is_current DESC, sort_order LIMIT 1",
                (row["id"],),
            ).fetchone()
            edu = self._conn.execute(
                "SELECT * FROM alumni_education WHERE alumni_id = ? ORDER BY sort_order LIMIT 1",
                (row["id"],),
            ).fetchone()
            alum = {
                "id": row["id"],
                "firstName": row["first_name"],
                "lastInitial": row["last_initial"],
                "role": work["title"] if work else row["headline"] or "",
                "company": work["company"] if work else "",
                "industry": work["industry"] if work else "",
                "graduationYear": edu["graduation_year"] if edu and edu["graduation_year"] is not None else 0,
                "major": edu["major"] if edu else "",
                "university": edu["school"] if edu else "",
                "yearsExperience": 0,
                "bio": row["bio"],
                "expertise": [],
                "topics": [],
                "responseTime": row["response_time"],
                "availability": row["availability"],
                "goalAlignment": [],
                "avatarGradient": row["avatar_gradient"],
                "linkedinUrl": row["linkedin_url"],
            }
            alum["expertise"] = [
                r["display_label"] or self._skill_name(r["skill_id"])
                for r in self._conn.execute(
                    "SELECT * FROM alumni_expertise WHERE alumni_id = ? ORDER BY sort_order", (row["id"],)
                )
            ]
            alum["topics"] = [
                r["topic"] for r in self._conn.execute(
                    "SELECT topic FROM alumni_topics WHERE alumni_id = ? ORDER BY sort_order", (row["id"],)
                )
            ]
            alum["goalAlignment"] = [
                r["catalog_goal_id"] for r in self._conn.execute(
                    "SELECT catalog_goal_id FROM alumni_goal_alignment WHERE alumni_id = ?", (row["id"],)
                )
            ]
            alumni.append(alum)
        return alumni

    def _save_alumni(self, alumni: Iterable[dict[str, Any]]) -> None:
        for table in (
            "alumni_goal_alignment", "alumni_topics", "alumni_expertise",
            "alumni_work_experiences", "alumni_education", "alumni",
        ):
            self._conn.execute(f"DELETE FROM {table}")
        for alum in alumni:
            self._conn.execute(
                "INSERT INTO alumni(id, first_name, last_initial, headline, bio, response_time, availability, "
                "avatar_gradient, linkedin_url) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (alum["id"], alum["firstName"], alum["lastInitial"], alum.get("headline") or alum.get("role"),
                 alum.get("bio", ""), alum.get("responseTime", ""), alum.get("availability", ""),
                 alum.get("avatarGradient", ""), alum.get("linkedinUrl", "")),
            )
            self._conn.execute(
                "INSERT INTO alumni_work_experiences(alumni_id, sort_order, title, company, industry, is_current) "
                "VALUES(?, 0, ?, ?, ?, 1)",
                (alum["id"], alum.get("role", ""), alum.get("company", ""), alum.get("industry", "")),
            )
            self._conn.execute(
                "INSERT INTO alumni_education(alumni_id, sort_order, school, major, graduation_year) VALUES(?, 0, ?, ?, ?)",
                (alum["id"], alum.get("university", ""), alum.get("major", ""), alum.get("graduationYear")),
            )
            for idx, expertise in enumerate(alum.get("expertise", [])):
                skill_id = self._get_or_create_skill(expertise)
                self._conn.execute(
                    "INSERT OR REPLACE INTO alumni_expertise(alumni_id, skill_id, display_label, sort_order) "
                    "VALUES(?, ?, NULL, ?)",
                    (alum["id"], skill_id, idx),
                )
            for idx, topic in enumerate(alum.get("topics", [])):
                self._conn.execute(
                    "INSERT OR REPLACE INTO alumni_topics(alumni_id, topic, sort_order) VALUES(?, ?, ?)",
                    (alum["id"], topic, idx),
                )
            for catalog_id in alum.get("goalAlignment", []):
                self._conn.execute(
                    "INSERT OR REPLACE INTO alumni_goal_alignment(alumni_id, catalog_goal_id) VALUES(?, ?)",
                    (alum["id"], catalog_id),
                )

    # ----- goals and tracking -----
    def _load_goals(self) -> dict[str, dict[str, dict[str, Any]]]:
        out: dict[str, dict[str, dict[str, Any]]] = {}
        for row in self._conn.execute("SELECT * FROM user_goals").fetchall():
            goal = {
                "id": row["id"], "catalogId": row["catalog_id"], "title": row["title"],
                "description": row["description"], "color": row["color"], "status": row["status"],
                "progress": row["progress"], "lastUpdated": row["last_updated"],
                "createdAt": row["created_at"], "confidence": {}, "sortOrder": row["sort_order"],
            }
            for c in self._conn.execute("SELECT skill_id, score FROM user_goal_confidence WHERE goal_id = ?", (row["id"],)):
                goal["confidence"][c["skill_id"]] = c["score"]
            out.setdefault(row["user_id"], {})[row["id"]] = goal
        return out

    def _save_goals(self, goals: Mapping[str, Mapping[str, dict[str, Any]]]) -> None:
        self._conn.execute("DELETE FROM user_goal_confidence")
        self._conn.execute("DELETE FROM user_goals")
        for user_id, by_id in goals.items():
            for goal in by_id.values():
                self._conn.execute(
                    "INSERT INTO user_goals(id, user_id, catalog_id, title, description, color, status, progress, "
                    "last_updated, created_at, sort_order) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (goal["id"], user_id, goal["catalogId"], goal["title"], goal["description"], goal["color"],
                     goal["status"], goal.get("progress", 0), goal.get("lastUpdated", ""), goal.get("createdAt", 0),
                     goal.get("sortOrder", 0)),
                )
                for skill_id, score in goal.get("confidence", {}).items():
                    self._conn.execute(
                        "INSERT OR REPLACE INTO user_goal_confidence(goal_id, skill_id, score) VALUES(?, ?, ?)",
                        (goal["id"], skill_id, score),
                    )

    def _load_tracking(self) -> dict[str, dict[str, dict[str, Any]]]:
        out: dict[str, dict[str, dict[str, Any]]] = {}
        for row in self._conn.execute(
            "SELECT gt.goal_id, gt.week_started_at, ug.user_id FROM goal_tracking gt JOIN user_goals ug ON ug.id = gt.goal_id"
        ).fetchall():
            tracking = {"modules": {}, "weekStartedAt": row["week_started_at"], "weekFocus": []}
            for mod in self._conn.execute("SELECT * FROM goal_tracking_modules WHERE goal_id = ?", (row["goal_id"],)):
                skill_id = mod["skill_id"]
                tracking["modules"][skill_id] = {
                    "completedSteps": [
                        r["step_index"] for r in self._conn.execute(
                            "SELECT step_index FROM goal_tracking_completed_steps WHERE goal_id = ? AND skill_id = ? ORDER BY step_index",
                            (row["goal_id"], skill_id),
                        )
                    ],
                    "consumedResources": [
                        r["resource_index"] for r in self._conn.execute(
                            "SELECT resource_index FROM goal_tracking_consumed_resources WHERE goal_id = ? AND skill_id = ? ORDER BY resource_index",
                            (row["goal_id"], skill_id),
                        )
                    ],
                    "stepsCompletedSinceRerate": mod["steps_completed_since_rerate"],
                    "rerateDismissed": bool(mod["rerate_dismissed"]),
                }
            tracking["weekFocus"] = [
                r["focus"] for r in self._conn.execute(
                    "SELECT focus FROM goal_tracking_week_focus WHERE goal_id = ? ORDER BY sort_order",
                    (row["goal_id"],),
                )
            ]
            out.setdefault(row["user_id"], {})[row["goal_id"]] = tracking
        return out

    def _save_tracking(self, tracking: Mapping[str, Mapping[str, dict[str, Any]]]) -> None:
        for table in (
            "goal_tracking_week_focus", "goal_tracking_consumed_resources",
            "goal_tracking_completed_steps", "goal_tracking_modules", "goal_tracking",
        ):
            self._conn.execute(f"DELETE FROM {table}")
        for _user_id, by_goal in tracking.items():
            for goal_id, tr in by_goal.items():
                self._conn.execute(
                    "INSERT INTO goal_tracking(goal_id, week_started_at) VALUES(?, ?)",
                    (goal_id, tr.get("weekStartedAt", 0)),
                )
                for skill_id, mod in tr.get("modules", {}).items():
                    self._conn.execute(
                        "INSERT INTO goal_tracking_modules(goal_id, skill_id, steps_completed_since_rerate, rerate_dismissed) "
                        "VALUES(?, ?, ?, ?)",
                        (goal_id, skill_id, mod.get("stepsCompletedSinceRerate", 0),
                         int(bool(mod.get("rerateDismissed", False)))),
                    )
                    for step in mod.get("completedSteps", []):
                        self._conn.execute(
                            "INSERT OR REPLACE INTO goal_tracking_completed_steps(goal_id, skill_id, step_index) VALUES(?, ?, ?)",
                            (goal_id, skill_id, step),
                        )
                    for res in mod.get("consumedResources", []):
                        self._conn.execute(
                            "INSERT OR REPLACE INTO goal_tracking_consumed_resources(goal_id, skill_id, resource_index) VALUES(?, ?, ?)",
                            (goal_id, skill_id, res),
                        )
                for idx, focus in enumerate(tr.get("weekFocus", [])):
                    self._conn.execute(
                        "INSERT OR REPLACE INTO goal_tracking_week_focus(goal_id, focus, sort_order) VALUES(?, ?, ?)",
                        (goal_id, focus, idx),
                    )

    # ----- applications and related -----
    def _load_saved_jobs(self) -> dict[str, dict[str, set[str]]]:
        out: dict[str, dict[str, set[str]]] = {}
        for row in self._conn.execute("SELECT * FROM saved_jobs").fetchall():
            out.setdefault(row["user_id"], {}).setdefault(row["goal_id"], set()).add(row["job_id"])
        return out

    def _save_saved_jobs(self, saved_jobs: Mapping[str, Mapping[str, set[str]]]) -> None:
        self._conn.execute("DELETE FROM saved_jobs")
        for user_id, by_goal in saved_jobs.items():
            for goal_id, job_ids in by_goal.items():
                for job_id in job_ids:
                    self._conn.execute(
                        "INSERT OR REPLACE INTO saved_jobs(user_id, goal_id, job_id, saved_at) VALUES(?, ?, ?, 0)",
                        (user_id, goal_id, job_id),
                    )

    def _load_applications(self) -> dict[str, dict[str, dict[str, Any]]]:
        out: dict[str, dict[str, dict[str, Any]]] = {}
        for row in self._conn.execute("SELECT * FROM applications").fetchall():
            app = {
                "id": row["id"], "kind": row["kind"], "goalId": row["goal_id"], "jobId": row["job_id"],
                "title": row["title"], "company": row["company"], "submittedAt": row["submitted_at"],
                "partnerStatus": row["partner_status"], "manualStatus": row["manual_status"],
            }
            out.setdefault(row["user_id"], {})[row["id"]] = app
        return out

    def _save_applications(self, applications: Mapping[str, Mapping[str, dict[str, Any]]]) -> None:
        self._conn.execute("DELETE FROM applications")
        for user_id, by_id in applications.items():
            for app in by_id.values():
                self._conn.execute(
                    "INSERT INTO applications(id, user_id, kind, goal_id, job_id, title, company, submitted_at, "
                    "partner_status, manual_status, cv_text) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (app["id"], user_id, app["kind"], app["goalId"], app["jobId"], app["title"], app["company"],
                     app["submittedAt"], app.get("partnerStatus"), app.get("manualStatus"), app.get("cvText")),
                )

    def _load_reviews(self) -> dict[str, dict[str, list[dict[str, Any]]]]:
        out: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for row in self._conn.execute("SELECT * FROM interview_reviews").fetchall():
            review = {
                "id": row["id"], "applicationId": row["application_id"], "fileName": row["file_name"],
                "uploadedAt": row["uploaded_at"], "durationSec": row["duration_sec"],
                "transcript": row["transcript"], "overallSummary": row["overall_summary"],
                "dimensions": _from_json(row["dimensions_json"], []),
                "improvementAdvice": row["improvement_advice"], "status": row["status"],
                "polls": row["polls"], "error": row["error"],
            }
            out.setdefault(row["user_id"], {}).setdefault(row["application_id"], []).append(review)
        return out

    def _save_reviews(self, reviews: Mapping[str, Mapping[str, list[dict[str, Any]]]]) -> None:
        self._conn.execute("DELETE FROM interview_reviews")
        for user_id, by_app in reviews.items():
            for app_id, items in by_app.items():
                for review in items:
                    self._conn.execute(
                        "INSERT INTO interview_reviews(id, user_id, application_id, file_name, uploaded_at, status, polls, "
                        "duration_sec, transcript, overall_summary, dimensions_json, improvement_advice, error) "
                        "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (review["id"], user_id, app_id, review.get("fileName", "audio"), review.get("uploadedAt", 0),
                         review.get("status", "transcribing"), review.get("polls", 0), review.get("durationSec"),
                         review.get("transcript", ""), review.get("overallSummary", ""), _json(review.get("dimensions", [])),
                         review.get("improvementAdvice", ""), review.get("error")),
                    )

    def _load_mocks(self) -> dict[str, dict[str, list[dict[str, Any]]]]:
        out: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for row in self._conn.execute("SELECT * FROM mock_interview_sessions").fetchall():
            session = {
                "id": row["id"], "applicationId": row["application_id"], "jobTitle": row["job_title"],
                "company": row["company"], "goalTitle": row["goal_title"],
                "skills": _from_json(row["skills_json"], []), "startedAt": row["started_at"],
                "completedAt": row["completed_at"], "durationSec": row["duration_sec"],
                "turns": [], "transcript": row["transcript"], "overallSummary": row["overall_summary"],
                "dimensions": _from_json(row["dimensions_json"], []),
                "improvementAdvice": row["improvement_advice"], "questions": _from_json(row["questions_json"], []),
                "currentIndex": row["current_index"], "status": row["status"], "error": row["error"],
            }
            for turn in self._conn.execute(
                "SELECT * FROM mock_interview_turns WHERE session_id = ? ORDER BY sort_order", (row["id"],)
            ):
                session["turns"].append(
                    {"id": turn["id"], "role": turn["role"], "text": turn["text"], "timestamp": turn["timestamp"]}
                )
            out.setdefault(row["user_id"], {}).setdefault(row["application_id"], []).append(session)
        return out

    def _save_mocks(self, mocks: Mapping[str, Mapping[str, list[dict[str, Any]]]]) -> None:
        self._conn.execute("DELETE FROM mock_interview_turns")
        self._conn.execute("DELETE FROM mock_interview_sessions")
        for user_id, by_app in mocks.items():
            for app_id, sessions in by_app.items():
                for session in sessions:
                    self._conn.execute(
                        "INSERT INTO mock_interview_sessions(id, user_id, application_id, job_title, company, goal_title, "
                        "skills_json, status, started_at, completed_at, duration_sec, transcript, overall_summary, "
                        "dimensions_json, improvement_advice, questions_json, current_index, error) "
                        "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (session["id"], user_id, app_id, session.get("jobTitle", ""), session.get("company", ""),
                         session.get("goalTitle"), _json(session.get("skills", [])), session.get("status", "in_progress"),
                         session.get("startedAt", 0), session.get("completedAt"), session.get("durationSec"),
                         session.get("transcript", ""), session.get("overallSummary", ""),
                         _json(session.get("dimensions", [])), session.get("improvementAdvice", ""),
                         _json(session.get("questions", [])), session.get("currentIndex", 0), session.get("error")),
                    )
                    for idx, turn in enumerate(session.get("turns", [])):
                        self._conn.execute(
                            "INSERT INTO mock_interview_turns(id, session_id, role, text, timestamp, sort_order) "
                            "VALUES(?, ?, ?, ?, ?, ?)",
                            (turn["id"], session["id"], turn["role"], turn["text"], turn["timestamp"], idx),
                        )

    def _load_tts_cache(self) -> dict[str, bytes]:
        return {row["turn_id"]: row["audio"] for row in self._conn.execute("SELECT * FROM tts_cache").fetchall()}

    def _save_tts_cache(self, tts_cache: Mapping[str, bytes]) -> None:
        self._conn.execute("DELETE FROM tts_cache")
        for turn_id, audio in tts_cache.items():
            self._conn.execute("INSERT INTO tts_cache(turn_id, audio, created_at) VALUES(?, ?, 0)", (turn_id, audio))

    # ----- meetings and notifications -----
    def _load_meetings(self) -> dict[str, dict[str, dict[str, Any]]]:
        out: dict[str, dict[str, dict[str, Any]]] = {}
        for row in self._conn.execute("SELECT * FROM meetings").fetchall():
            meeting = {
                "id": row["id"], "alumniId": row["alumni_id"], "topic": row["topic"], "message": row["message"],
                "preferredTimes": [
                    r["preferred_time"] for r in self._conn.execute(
                        "SELECT preferred_time FROM meeting_preferred_times WHERE meeting_id = ? ORDER BY sort_order",
                        (row["id"],),
                    )
                ],
                "submittedAt": row["submitted_at"], "status": row["status"], "completedAt": row["completed_at"],
            }
            out.setdefault(row["user_id"], {})[row["id"]] = meeting
        return out

    def _save_meetings(self, meetings: Mapping[str, Mapping[str, dict[str, Any]]]) -> None:
        self._conn.execute("DELETE FROM meeting_preferred_times")
        self._conn.execute("DELETE FROM meetings")
        for user_id, by_id in meetings.items():
            for meeting in by_id.values():
                self._conn.execute(
                    "INSERT INTO meetings(id, user_id, alumni_id, topic, message, submitted_at, status, completed_at) "
                    "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                    (meeting["id"], user_id, meeting["alumniId"], meeting["topic"], meeting["message"],
                     meeting["submittedAt"], meeting["status"], meeting.get("completedAt")),
                )
                for idx, preferred in enumerate(meeting.get("preferredTimes", [])):
                    self._conn.execute(
                        "INSERT OR REPLACE INTO meeting_preferred_times(meeting_id, preferred_time, sort_order) VALUES(?, ?, ?)",
                        (meeting["id"], preferred, idx),
                    )

    def _load_notifications(self) -> dict[str, list[dict[str, Any]]]:
        out: dict[str, list[dict[str, Any]]] = {}
        for row in self._conn.execute("SELECT * FROM notifications ORDER BY created_at DESC").fetchall():
            item = {
                "id": row["id"], "type": row["type"], "severity": row["severity"], "title": row["title"],
                "body": row["body"], "link": row["link"], "createdAt": row["created_at"],
                "read": bool(row["read"]), "dedupKey": row["dedup_key"],
            }
            out.setdefault(row["user_id"], []).append(item)
        return out

    def _save_notifications(self, notifications: Mapping[str, list[dict[str, Any]]]) -> None:
        self._conn.execute("DELETE FROM notifications")
        for user_id, items in notifications.items():
            for item in items:
                self._conn.execute(
                    "INSERT INTO notifications(id, user_id, type, severity, title, body, link, created_at, read, dedup_key) "
                    "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (item["id"], user_id, item["type"], item["severity"], item["title"], item["body"],
                     item.get("link"), item["createdAt"], int(bool(item.get("read", False))), item.get("dedupKey")),
                )

    # ----- helpers -----
    def _purge_tts_for(self, user_id: str) -> None:
        """Drop cached TTS audio belonging to the user's mock-interview turns."""
        for sessions in self.mocks.get(user_id, {}).values():
            for session in sessions:
                for turn in session.get("turns", []):
                    self.tts_cache.pop(turn.get("id", ""), None)

    def reset_user_data(self, user_id: str) -> None:
        """Clear demo data but keep the account (use-case SET-07)."""
        self._purge_tts_for(user_id)
        self.profiles[user_id] = None
        self.onboarding_chats[user_id] = None
        self.goals[user_id] = {}
        self.tracking[user_id] = {}
        self.saved_jobs[user_id] = {}
        self.applications[user_id] = {}
        self.reviews[user_id] = {}
        self.mocks[user_id] = {}
        self.meetings[user_id] = {}
        self.notifications[user_id] = []

    def delete_account(self, user_id: str) -> None:
        """Remove the account and all of its data (use-case SET-08)."""
        self._purge_tts_for(user_id)
        user = self.users.pop(user_id, None)
        if user:
            self.email_index.pop(user.email.lower(), None)
        for jti, uid in list(self.refresh_jti.items()):
            if uid == user_id:
                self.refresh_jti.pop(jti, None)
        for bucket in (
            self.user_settings,
            self.profiles,
            self.onboarding_chats,
            self.goals,
            self.tracking,
            self.saved_jobs,
            self.applications,
            self.reviews,
            self.mocks,
            self.meetings,
            self.notifications,
        ):
            bucket.pop(user_id, None)

    def get_catalog_goal(self, catalog_id: str) -> dict[str, Any] | None:
        return next((g for g in self.goal_catalog if g["id"] == catalog_id), None)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        return next((j for j in self.jobs if j["id"] == job_id), None)

    def get_alumni(self, alumni_id: str) -> dict[str, Any] | None:
        return next((a for a in self.alumni if a["id"] == alumni_id), None)


store = Store(settings.local_database_path)


def seed_catalogs() -> None:
    """Ensure public catalogs are present in the local SQLite database."""
    missing = [name for name in Store._catalog_buckets if not getattr(store, name)]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"Missing catalog data in SQLite database: {joined}")
