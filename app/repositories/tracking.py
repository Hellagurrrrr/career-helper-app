"""Goal tracking repository (parent + 4 child tables).

``goal_tracking`` plus per-skill modules, completed steps, consumed resources and
weekly focus. ``save`` replaces just one goal's tracking (children cascade via
FK) rather than rewriting every goal's tracking. ``get_or_default`` returns a
fresh in-memory default when no row exists (no phantom row on read).

Tracking is deleted implicitly: ``goal_tracking.goal_id`` references
``user_goals(id) ON DELETE CASCADE``, so deleting a goal removes its tracking.

Like the other aggregates, the working-dict keeps the camelCase shape the schema
(``app.schemas.tracking.GoalTracking``) and router use; the repo maps it to/from
the snake_case columns.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.core.security import now_ms


def default_tracking() -> dict[str, Any]:
    """A fresh GoalTracking aggregate (api-design 5.1)."""
    return {"modules": {}, "weekStartedAt": now_ms(), "weekFocus": []}


def get(conn: sqlite3.Connection, goal_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM goal_tracking WHERE goal_id = ?", (goal_id,)
    ).fetchone()
    if row is None:
        return None
    tracking: dict[str, Any] = {
        "modules": {},
        "weekStartedAt": row["week_started_at"],
        "weekFocus": [],
    }
    for mod in conn.execute(
        "SELECT * FROM goal_tracking_modules WHERE goal_id = ?", (goal_id,)
    ):
        skill_id = mod["skill_id"]
        tracking["modules"][skill_id] = {
            "completedSteps": [
                r["step_index"]
                for r in conn.execute(
                    "SELECT step_index FROM goal_tracking_completed_steps "
                    "WHERE goal_id = ? AND skill_id = ? ORDER BY step_index",
                    (goal_id, skill_id),
                )
            ],
            "consumedResources": [
                r["resource_index"]
                for r in conn.execute(
                    "SELECT resource_index FROM goal_tracking_consumed_resources "
                    "WHERE goal_id = ? AND skill_id = ? ORDER BY resource_index",
                    (goal_id, skill_id),
                )
            ],
            "stepsCompletedSinceRerate": mod["steps_completed_since_rerate"],
            "rerateDismissed": bool(mod["rerate_dismissed"]),
        }
    tracking["weekFocus"] = [
        r["focus"]
        for r in conn.execute(
            "SELECT focus FROM goal_tracking_week_focus WHERE goal_id = ? ORDER BY sort_order",
            (goal_id,),
        )
    ]
    return tracking


def get_or_default(conn: sqlite3.Connection, goal_id: str) -> dict[str, Any]:
    existing = get(conn, goal_id)
    return existing if existing is not None else default_tracking()


def save(conn: sqlite3.Connection, goal_id: str, tracking: dict[str, Any]) -> None:
    """Persist one goal's tracking aggregate (children replaced via cascade)."""
    conn.execute("DELETE FROM goal_tracking WHERE goal_id = ?", (goal_id,))
    conn.execute(
        "INSERT INTO goal_tracking(goal_id, week_started_at) VALUES(?, ?)",
        (goal_id, tracking.get("weekStartedAt", 0)),
    )
    for skill_id, mod in tracking.get("modules", {}).items():
        conn.execute(
            "INSERT INTO goal_tracking_modules"
            "(goal_id, skill_id, steps_completed_since_rerate, rerate_dismissed) VALUES(?, ?, ?, ?)",
            (goal_id, skill_id, mod.get("stepsCompletedSinceRerate", 0),
             int(bool(mod.get("rerateDismissed", False)))),
        )
        for step in mod.get("completedSteps", []):
            conn.execute(
                "INSERT OR REPLACE INTO goal_tracking_completed_steps(goal_id, skill_id, step_index) "
                "VALUES(?, ?, ?)",
                (goal_id, skill_id, step),
            )
        for res in mod.get("consumedResources", []):
            conn.execute(
                "INSERT OR REPLACE INTO goal_tracking_consumed_resources(goal_id, skill_id, resource_index) "
                "VALUES(?, ?, ?)",
                (goal_id, skill_id, res),
            )
    for idx, focus in enumerate(tracking.get("weekFocus", [])):
        conn.execute(
            "INSERT OR REPLACE INTO goal_tracking_week_focus(goal_id, focus, sort_order) VALUES(?, ?, ?)",
            (goal_id, focus, idx),
        )
