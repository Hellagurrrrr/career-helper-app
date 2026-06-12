from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class UserRecord:
    id: str
    email: str
    name: str
    password_hash: str
    created_at: int


@dataclass
class Store:
    """Process-wide in-memory repository.

    All user-owned collections are keyed by user_id. Public catalogs
    (goal_catalog / jobs / alumni) are shared and seeded on startup.
    Data is lost on restart by design (mock backend).
    """

    # --- auth ---
    users: dict[str, UserRecord] = field(default_factory=dict)
    email_index: dict[str, str] = field(default_factory=dict)  # email_lower -> user_id
    refresh_jti: dict[str, str] = field(default_factory=dict)  # jti -> user_id (valid refresh tokens)

    # --- profile ---
    profiles: dict[str, dict[str, Any]] = field(default_factory=dict)  # user_id -> Profile dict
    cv_tasks: dict[str, dict[str, Any]] = field(default_factory=dict)  # task_id -> task state
    onboarding_chats: dict[str, dict[str, Any]] = field(default_factory=dict)  # user_id -> chat session (resumable)

    # --- goals & tracking ---
    goals: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)     # user_id -> goal_id -> UserGoal
    tracking: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)  # user_id -> goal_id -> GoalTracking

    # --- jobs ---
    saved_jobs: dict[str, dict[str, set[str]]] = field(default_factory=dict)  # user_id -> goal_id -> {job_id}

    # --- applications & coaching ---
    applications: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)  # user_id -> app_id -> JobApplication
    reviews: dict[str, dict[str, list[dict[str, Any]]]] = field(default_factory=dict)  # user_id -> app_id -> [review]
    mocks: dict[str, dict[str, list[dict[str, Any]]]] = field(default_factory=dict)    # user_id -> app_id -> [session]

    # --- alumni meetings ---
    meetings: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)  # user_id -> meeting_id -> MeetingRequest

    # --- notifications ---
    notifications: dict[str, list[dict[str, Any]]] = field(default_factory=dict)  # user_id -> [notification]

    # --- public catalogs (shared) ---
    goal_catalog: list[dict[str, Any]] = field(default_factory=list)
    jobs: list[dict[str, Any]] = field(default_factory=list)
    alumni: list[dict[str, Any]] = field(default_factory=list)

    # ----- helpers -----
    def ensure_user_buckets(self, user_id: str) -> None:
        self.profiles.setdefault(user_id, None)  # type: ignore[arg-type]
        self.onboarding_chats.setdefault(user_id, None)  # type: ignore[arg-type]
        self.goals.setdefault(user_id, {})
        self.tracking.setdefault(user_id, {})
        self.saved_jobs.setdefault(user_id, {})
        self.applications.setdefault(user_id, {})
        self.reviews.setdefault(user_id, {})
        self.mocks.setdefault(user_id, {})
        self.meetings.setdefault(user_id, {})
        self.notifications.setdefault(user_id, [])

    def reset_user_data(self, user_id: str) -> None:
        """Clear demo data but keep the account (use-case SET-07)."""
        self.profiles[user_id] = None  # type: ignore[assignment]
        self.onboarding_chats[user_id] = None  # type: ignore[assignment]
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
        user = self.users.pop(user_id, None)
        if user:
            self.email_index.pop(user.email.lower(), None)
        for jti, uid in list(self.refresh_jti.items()):
            if uid == user_id:
                self.refresh_jti.pop(jti, None)
        for bucket in (
            self.profiles, self.onboarding_chats, self.goals, self.tracking, self.saved_jobs,
            self.applications, self.reviews, self.mocks, self.meetings, self.notifications,
        ):
            bucket.pop(user_id, None)  # type: ignore[arg-type]

    def get_catalog_goal(self, catalog_id: str) -> dict[str, Any] | None:
        return next((g for g in self.goal_catalog if g["id"] == catalog_id), None)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        return next((j for j in self.jobs if j["id"] == job_id), None)

    def get_alumni(self, alumni_id: str) -> dict[str, Any] | None:
        return next((a for a in self.alumni if a["id"] == alumni_id), None)


store = Store()


def seed_catalogs() -> None:
    """Populate public catalogs. Imported lazily to avoid circular imports."""
    from app.data.goal_catalog import GOAL_CATALOG
    from app.data.jobs import JOBS
    from app.data.alumni import ALUMNI

    store.goal_catalog = [dict(g) for g in GOAL_CATALOG]
    store.jobs = [dict(j) for j in JOBS]
    store.alumni = [dict(a) for a in ALUMNI]
