from __future__ import annotations

import time
from typing import Any

from app.services import progress as progress_svc
from app.services.store import store


def new_tracking() -> dict[str, Any]:
    """Default GoalTracking (api-design 5.1)."""
    return {
        "modules": {},
        "weekStartedAt": int(time.time() * 1000),
        "weekFocus": [],
    }


def recompute_progress(user_id: str, goal_id: str) -> None:
    """Recalculate UserGoal.progress from confidence + tracking and persist it.

    Also emits milestone notifications when progress crosses 25/50/75/100 (NT-05).
    """
    goal = store.goals.get(user_id, {}).get(goal_id)
    if not goal:
        return
    catalog = store.get_catalog_goal(goal["catalogId"]) or {}
    tracking = store.tracking.get(user_id, {}).get(goal_id)
    old_progress = goal.get("progress", 0)
    new_progress = progress_svc.compute_progress(goal.get("confidence", {}), catalog, tracking)
    goal["progress"] = new_progress
    goal["lastUpdated"] = _iso_now()

    if new_progress > old_progress:
        from app.services import notifications_service

        notifications_service.check_milestone(
            user_id, goal_id, old_progress, new_progress, goal["title"]
        )


def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
