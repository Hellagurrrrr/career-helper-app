from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.errors import goal_already_added, not_found, validation_error
from app.core.security import new_id, now_ms
from app.schemas.goals import (
    CatalogGoal,
    CreateGoalRequest,
    ReorderGoalsRequest,
    UpdateGoalRequest,
    UserGoal,
)
from app.services import mock_match
from app.services.goals_service import new_tracking, recompute_progress
from app.services.store import UserRecord, store

router = APIRouter(tags=["goals"])


# ----- public catalog -----
@router.get("/goal-catalog", response_model=list[CatalogGoal])
def get_goal_catalog(user: UserRecord = Depends(get_current_user)) -> list[dict]:
    profile = store.profiles.get(user.id)
    return mock_match.sort_catalog_goals(profile, store.goal_catalog)


@router.get("/goal-catalog/{catalog_id}", response_model=CatalogGoal)
def get_catalog_item(catalog_id: str, user: UserRecord = Depends(get_current_user)) -> dict:
    item = store.get_catalog_goal(catalog_id)
    if not item:
        raise not_found("Catalog goal not found.")
    return item


# ----- user goals -----
@router.get("/goals", response_model=list[UserGoal])
def list_goals(user: UserRecord = Depends(get_current_user)) -> list[dict]:
    goals = list(store.goals.get(user.id, {}).values())
    return sorted(goals, key=lambda g: g["sortOrder"])


@router.post("/goals", response_model=UserGoal, status_code=201)
def create_goal(body: CreateGoalRequest, user: UserRecord = Depends(get_current_user)) -> dict:
    catalog = store.get_catalog_goal(body.catalog_id)
    if not catalog:
        raise not_found("Catalog goal not found.")

    user_goals = store.goals.setdefault(user.id, {})
    if any(g["catalogId"] == body.catalog_id for g in user_goals.values()):
        raise goal_already_added()

    goal_id = new_id("g")
    sort_order = len(user_goals)
    goal = {
        "id": goal_id,
        "catalogId": catalog["id"],
        "title": catalog["title"],
        "description": catalog["description"],
        "color": catalog["color"],
        "status": catalog["defaultStatus"],
        "progress": 0,
        "lastUpdated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "createdAt": now_ms(),
        "confidence": {},
        "sortOrder": sort_order,
    }
    user_goals[goal_id] = goal
    store.tracking.setdefault(user.id, {})[goal_id] = new_tracking()
    recompute_progress(user.id, goal_id)
    return goal


@router.get("/goals/{goal_id}", response_model=UserGoal)
def get_goal(goal_id: str, user: UserRecord = Depends(get_current_user)) -> dict:
    goal = store.goals.get(user.id, {}).get(goal_id)
    if not goal:
        raise not_found("Goal not found.")
    return goal


@router.patch("/goals/{goal_id}", response_model=UserGoal)
def update_goal(
    goal_id: str,
    body: UpdateGoalRequest,
    user: UserRecord = Depends(get_current_user),
) -> dict:
    goal = store.goals.get(user.id, {}).get(goal_id)
    if not goal:
        raise not_found("Goal not found.")

    if body.status is not None:
        goal["status"] = body.status
    if body.confidence is not None:
        for value in body.confidence.values():
            if not 1 <= value <= 5:
                raise validation_error("Confidence must be between 1 and 5.", "confidence")
        goal.setdefault("confidence", {}).update(body.confidence)

    recompute_progress(user.id, goal_id)
    return goal


@router.delete("/goals/{goal_id}", status_code=204, response_model=None)
def delete_goal(goal_id: str, user: UserRecord = Depends(get_current_user)) -> None:
    user_goals = store.goals.get(user.id, {})
    if goal_id not in user_goals:
        raise not_found("Goal not found.")
    user_goals.pop(goal_id, None)
    store.tracking.get(user.id, {}).pop(goal_id, None)
    store.saved_jobs.get(user.id, {}).pop(goal_id, None)
    # Re-pack sortOrder to stay contiguous.
    for idx, g in enumerate(sorted(user_goals.values(), key=lambda x: x["sortOrder"])):
        g["sortOrder"] = idx


@router.put("/goals/order", response_model=list[UserGoal])
def reorder_goals(body: ReorderGoalsRequest, user: UserRecord = Depends(get_current_user)) -> list[dict]:
    user_goals = store.goals.get(user.id, {})
    if set(body.goal_ids) != set(user_goals.keys()):
        raise validation_error("goalIds must include every goal exactly once.", "goalIds")
    for idx, gid in enumerate(body.goal_ids):
        user_goals[gid]["sortOrder"] = idx
    return sorted(user_goals.values(), key=lambda g: g["sortOrder"])
