from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.errors import not_found, validation_error
from app.core.security import now_ms
from app.db import get_conn
from app.repositories import goals as goals_repo
from app.repositories import tracking as tracking_repo
from app.schemas.tracking import (
    GoalTracking,
    ResourceToggleRequest,
    StepToggleRequest,
    WeekFocusRequest,
)
from app.services.goals_service import recompute_progress
from app.services.store import UserRecord, store

router = APIRouter(prefix="/goals/{goal_id}/tracking", tags=["tracking"])


def _get_goal_or_404(conn: sqlite3.Connection, user_id: str, goal_id: str) -> dict[str, Any]:
    goal = goals_repo.get(conn, user_id, goal_id)
    if not goal:
        raise not_found("Goal not found.")
    return goal


def _get_module(tracking: dict[str, Any], skill_id: str) -> dict[str, Any]:
    modules = tracking.setdefault("modules", {})
    if skill_id not in modules:
        modules[skill_id] = {
            "completedSteps": [],
            "consumedResources": [],
            "stepsCompletedSinceRerate": 0,
            "rerateDismissed": False,
        }
    return modules[skill_id]


def _catalog_skill(goal: dict[str, Any], skill_id: str) -> dict[str, Any]:
    catalog = store.get_catalog_goal(goal["catalogId"]) or {}
    skill = next((s for s in catalog.get("coreSkills", []) if s["id"] == skill_id), None)
    if not skill:
        raise not_found("Skill module not found for this goal.")
    return skill


@router.get("", response_model=GoalTracking)
def get_tracking(
    goal_id: str,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    '''
    Get the tracking for a goal.

    **Args**:
        - goal_id: str: The ID of the goal to get tracking for.
        - user: UserRecord: The current user.
    **Returns**:
        - GoalTracking: The tracking for the goal.
    '''
    _get_goal_or_404(conn, user.id, goal_id)
    return tracking_repo.get_or_default(conn, goal_id)


@router.put("/modules/{skill_id}/steps/{step_index}", response_model=GoalTracking)
def toggle_step(
    goal_id: str,
    skill_id: str,
    step_index: int,
    body: StepToggleRequest,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    '''
    Toggle a step for a goal.

    **Args**:
        - goal_id: str: The ID of the goal to toggle the step for.
        - skill_id: str: The ID of the skill to toggle the step for.
        - step_index: int: The index of the step to toggle.
        - body: StepToggleRequest: The request body containing the completed status of the step.
        - user: UserRecord: The current user.
    **Returns**:
        - GoalTracking: The tracking for the goal.
    '''
    goal = _get_goal_or_404(conn, user.id, goal_id)
    skill = _catalog_skill(goal, skill_id)
    if not 0 <= step_index < len(skill.get("whatToDo", [])):
        raise validation_error("step_index out of range.", "stepIndex")

    tracking = tracking_repo.get_or_default(conn, goal_id)
    module = _get_module(tracking, skill_id)
    steps = set(module["completedSteps"])
    if body.completed:
        if step_index not in steps:
            steps.add(step_index)
            module["stepsCompletedSinceRerate"] += 1
    else:
        steps.discard(step_index)
    module["completedSteps"] = sorted(steps)

    tracking_repo.save(conn, goal_id, tracking)
    recompute_progress(conn, user.id, goal_id)
    return tracking


@router.put("/modules/{skill_id}/resources/{resource_index}", response_model=GoalTracking)
def toggle_resource(
    goal_id: str,
    skill_id: str,
    resource_index: int,
    body: ResourceToggleRequest,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    '''
    Toggle a resource for a goal.

    **Args**:
        - goal_id: str: The ID of the goal to toggle the resource for.
        - skill_id: str: The ID of the skill to toggle the resource for.
        - resource_index: int: The index of the resource to toggle.
        - body: ResourceToggleRequest: The request body containing the consumed status of the resource.
        - user: UserRecord: The current user.
    **Returns**:
        - GoalTracking: The tracking for the goal.
    '''
    goal = _get_goal_or_404(conn, user.id, goal_id)
    skill = _catalog_skill(goal, skill_id)
    if not 0 <= resource_index < len(skill.get("resources", [])):
        raise validation_error("resource_index out of range.", "resourceIndex")

    tracking = tracking_repo.get_or_default(conn, goal_id)
    module = _get_module(tracking, skill_id)
    consumed = set(module["consumedResources"])
    if body.consumed:
        consumed.add(resource_index)
    else:
        consumed.discard(resource_index)
    module["consumedResources"] = sorted(consumed)

    tracking_repo.save(conn, goal_id, tracking)
    return tracking


@router.post("/modules/{skill_id}/rerate-dismiss", response_model=GoalTracking)
def rerate_dismiss(
    goal_id: str,
    skill_id: str,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    '''
    Dismiss the rerate for a goal.

    **Args**:
        - goal_id: str: The ID of the goal to dismiss the rerate for.
        - skill_id: str: The ID of the skill to dismiss the rerate for.
        - user: UserRecord: The current user.
    **Returns**:
        - GoalTracking: The tracking for the goal.
    '''
    goal = _get_goal_or_404(conn, user.id, goal_id)
    _catalog_skill(goal, skill_id)
    tracking = tracking_repo.get_or_default(conn, goal_id)
    module = _get_module(tracking, skill_id)
    module["rerateDismissed"] = True
    module["stepsCompletedSinceRerate"] = 0

    tracking_repo.save(conn, goal_id, tracking)
    return tracking


@router.put("/week-focus", response_model=GoalTracking)
def set_week_focus(
    goal_id: str,
    body: WeekFocusRequest,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    '''
    Set the week focus for a goal.

    **Args**:
        - goal_id: str: The ID of the goal to set the week focus for.
        - body: WeekFocusRequest: The request body containing the week focus.
        - user: UserRecord: The current user.
    **Returns**:
        - GoalTracking: The tracking for the goal.
    '''
    _get_goal_or_404(conn, user.id, goal_id)
    tracking = tracking_repo.get_or_default(conn, goal_id)
    tracking["weekFocus"] = body.week_focus
    tracking["weekStartedAt"] = now_ms()

    tracking_repo.save(conn, goal_id, tracking)
    return tracking
