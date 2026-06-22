from __future__ import annotations

import base64
import json
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


def _encode(value: StoreValue) -> StoreValue:
    if isinstance(value, UserRecord):
        return {"__type__": "UserRecord", "value": asdict(value)}
    if isinstance(value, bytes):
        return {"__type__": "bytes", "value": base64.b64encode(value).decode("ascii")}
    if isinstance(value, (PersistentSet, set)):
        return {"__type__": "set", "value": [_encode(v) for v in value]}
    if isinstance(value, (PersistentDict, dict)):
        return {str(k): _encode(v) for k, v in value.items()}
    if isinstance(value, (PersistentList, list)):
        return [_encode(v) for v in value]
    return value


def _decode(value: StoreValue) -> StoreValue:
    if isinstance(value, dict) and value.get("__type__") == "UserRecord":
        return UserRecord(**value["value"])
    if isinstance(value, dict) and value.get("__type__") == "bytes":
        return base64.b64decode(value["value"].encode("ascii"))
    if isinstance(value, dict) and value.get("__type__") == "set":
        return set(_decode(v) for v in value["value"])
    if isinstance(value, dict):
        return {k: _decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_decode(v) for v in value]
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
    """SQLite-backed local repository with the original dict-like interface."""

    _bucket_defaults: dict[str, StoreValue] = {
        "users": {},
        "email_index": {},
        "refresh_jti": {},
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
        conn = sqlite3.connect(self.database_path, check_same_thread=False)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS store_buckets ("
            "name TEXT PRIMARY KEY, "
            "value TEXT NOT NULL"
            ")"
        )
        object.__setattr__(self, "_conn", conn)

        for name, default in self._bucket_defaults.items():
            value = self._load_bucket(name, default)
            object.__setattr__(self, name, _wrap(value, lambda bucket=name: self._save_bucket(bucket)))

        object.__setattr__(self, "_loading", False)

    def __setattr__(self, name: str, value: StoreValue) -> None:
        if name in self._bucket_defaults:
            object.__setattr__(self, name, _wrap(value, lambda bucket=name: self._save_bucket(bucket)))
            if not getattr(self, "_loading", False):
                self._save_bucket(name)
            return
        object.__setattr__(self, name, value)

    def _load_bucket(self, name: str, default: StoreValue) -> StoreValue:
        row = self._conn.execute("SELECT value FROM store_buckets WHERE name = ?", (name,)).fetchone()
        if not row:
            return default.copy() if isinstance(default, (dict, list, set)) else default
        return _decode(json.loads(row[0]))

    def _save_bucket(self, name: str) -> None:
        if self._loading:
            return
        payload = json.dumps(_encode(getattr(self, name)), separators=(",", ":"), sort_keys=True)
        self._conn.execute(
            "INSERT INTO store_buckets(name, value) VALUES(?, ?) "
            "ON CONFLICT(name) DO UPDATE SET value = excluded.value",
            (name, payload),
        )
        self._conn.commit()

    def reset_all(self) -> None:
        for name, default in self._bucket_defaults.items():
            setattr(self, name, default.copy() if isinstance(default, (dict, list, set)) else default)

    def ensure_user_buckets(self, user_id: str) -> None:
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
    """Populate public catalogs. Imported lazily to avoid circular imports."""
    from app.data.alumni import ALUMNI
    from app.data.goal_catalog import GOAL_CATALOG
    from app.data.jobs import JOBS

    store.goal_catalog = [dict(g) for g in GOAL_CATALOG]
    store.jobs = [dict(j) for j in JOBS]
    store.alumni = [dict(a) for a in ALUMNI]
