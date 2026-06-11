from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.errors import not_found, validation_error
from app.schemas.tracking import (
    GoalTracking,
    ResourceToggleRequest,
    StepToggleRequest,
    WeekFocusRequest,
)
from app.services.goals_service import new_tracking, recompute_progress
from app.services.store import UserRecord, store

router = APIRouter(prefix="/goals/{goal_id}/tracking", tags=["tracking"])


def _get_goal_or_404(user_id: str, goal_id: str) -> dict[str, Any]:
    goal = store.goals.get(user_id, {}).get(goal_id)
    if not goal:
        raise not_found("Goal not found.")
    return goal


def _get_tracking(user_id: str, goal_id: str) -> dict[str, Any]:
    tracking_bucket = store.tracking.setdefault(user_id, {})
    if goal_id not in tracking_bucket:
        tracking_bucket[goal_id] = new_tracking()
    return tracking_bucket[goal_id]


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
def get_tracking(goal_id: str, user: UserRecord = Depends(get_current_user)) -> dict:
    _get_goal_or_404(user.id, goal_id)
    return _get_tracking(user.id, goal_id)


@router.put("/modules/{skill_id}/steps/{step_index}", response_model=GoalTracking)
def toggle_step(
    goal_id: str,
    skill_id: str,
    step_index: int,
    body: StepToggleRequest,
    user: UserRecord = Depends(get_current_user),
) -> dict:
    goal = _get_goal_or_404(user.id, goal_id)
    skill = _catalog_skill(goal, skill_id)
    if not 0 <= step_index < len(skill.get("whatToDo", [])):
        raise validation_error("step_index out of range.", "stepIndex")

    tracking = _get_tracking(user.id, goal_id)
    module = _get_module(tracking, skill_id)
    steps = set(module["completedSteps"])
    if body.completed:
        if step_index not in steps:
            steps.add(step_index)
            module["stepsCompletedSinceRerate"] += 1
    else:
        steps.discard(step_index)
    module["completedSteps"] = sorted(steps)

    recompute_progress(user.id, goal_id)
    return tracking


@router.put("/modules/{skill_id}/resources/{resource_index}", response_model=GoalTracking)
def toggle_resource(
    goal_id: str,
    skill_id: str,
    resource_index: int,
    body: ResourceToggleRequest,
    user: UserRecord = Depends(get_current_user),
) -> dict:
    goal = _get_goal_or_404(user.id, goal_id)
    skill = _catalog_skill(goal, skill_id)
    if not 0 <= resource_index < len(skill.get("resources", [])):
        raise validation_error("resource_index out of range.", "resourceIndex")

    tracking = _get_tracking(user.id, goal_id)
    module = _get_module(tracking, skill_id)
    consumed = set(module["consumedResources"])
    if body.consumed:
        consumed.add(resource_index)
    else:
        consumed.discard(resource_index)
    module["consumedResources"] = sorted(consumed)
    return tracking


@router.post("/modules/{skill_id}/rerate-dismiss", response_model=GoalTracking)
def rerate_dismiss(
    goal_id: str,
    skill_id: str,
    user: UserRecord = Depends(get_current_user),
) -> dict:
    goal = _get_goal_or_404(user.id, goal_id)
    _catalog_skill(goal, skill_id)
    tracking = _get_tracking(user.id, goal_id)
    module = _get_module(tracking, skill_id)
    module["rerateDismissed"] = True
    module["stepsCompletedSinceRerate"] = 0
    return tracking


@router.put("/week-focus", response_model=GoalTracking)
def set_week_focus(
    goal_id: str,
    body: WeekFocusRequest,
    user: UserRecord = Depends(get_current_user),
) -> dict:
    _get_goal_or_404(user.id, goal_id)
    tracking = _get_tracking(user.id, goal_id)
    tracking["weekFocus"] = body.week_focus
    return tracking
