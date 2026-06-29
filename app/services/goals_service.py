from __future__ import annotations

import sqlite3
import time

from app.repositories import catalogs as catalogs_repo
from app.repositories import goals as goals_repo
from app.repositories import tracking as tracking_repo
from app.services import progress as progress_svc


def recompute_progress(conn: sqlite3.Connection, user_id: str, goal_id: str) -> None:
    """Recalculate UserGoal.progress from confidence + tracking and persist it.

    Also emits milestone notifications when progress crosses 25/50/75/100 (NT-05).
    """
    goal = goals_repo.get(conn, user_id, goal_id)
    if not goal:
        return
    catalog = catalogs_repo.get_catalog_goal(conn, goal["catalogId"]) or {}
    tracking = tracking_repo.get(conn, goal_id)
    old_progress = goal["progress"]
    new_progress = progress_svc.compute_progress(goal["confidence"], catalog, tracking)
    goals_repo.set_progress(conn, goal_id, new_progress, _iso_now())

    if new_progress > old_progress:
        from app.services import notifications_service

        notifications_service.check_milestone(
            user_id, goal_id, old_progress, new_progress, goal["title"]
        )


def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
