from __future__ import annotations

import sqlite3
import time

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.errors import goal_already_added, not_found, validation_error
from app.core.security import new_id, now_ms
from app.db import get_conn
from app.repositories import catalogs as catalogs_repo
from app.repositories import goals as goals_repo
from app.repositories import profiles as profiles_repo
from app.schemas.goals import (
    CatalogGoal,
    CreateGoalRequest,
    ReorderGoalsRequest,
    UpdateGoalRequest,
    UserGoal,
)
from app.services import mock_match
from app.services.goals_service import recompute_progress
from app.services.store import UserRecord

router = APIRouter(tags=["goals"])


# ----- public catalog -----
@router.get("/goal-catalog", response_model=list[CatalogGoal])
def get_goal_catalog(
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[dict]:
    '''
    Get the goal catalog.

    **Args**:
        - user: UserRecord: The current user.
    **Returns**:
        - list[CatalogGoal]: The goal catalog, sorted by descending match score.
    '''
    profile = profiles_repo.get(conn, user.id)
    return mock_match.sort_catalog_goals(profile, catalogs_repo.list_goal_catalog(conn))


@router.get("/goal-catalog/{catalog_id}", response_model=CatalogGoal)
def get_catalog_item(
    catalog_id: str,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    '''
    Get a goal catalog item.

    **Args**:
        - catalog_id: str: The ID of the catalog item.
        - user: UserRecord: The current user.
    **Returns**:
        - CatalogGoal: The catalog item.
    '''
    item = catalogs_repo.get_catalog_goal(conn, catalog_id)
    if not item:
        raise not_found("Catalog goal not found.")
    return item


# ----- user goals -----
@router.get("/goals", response_model=list[UserGoal])
def list_goals(
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[dict]:
    '''
    Get the list of goals that the current user has selected.

    **Args**:
        - user: UserRecord: The current user.
    **Returns**:
        - list[UserGoal]: The list of goals for the current user, sorted by sortOrder.
    '''
    return goals_repo.list_for_user(conn, user.id)


@router.post("/goals", response_model=UserGoal, status_code=201)
def create_goal(
    body: CreateGoalRequest,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    '''
    Create a new goal for the current user.

    **Args**:
        - body: CreateGoalRequest: The request body containing the catalog ID of the goal to create.
        - user: UserRecord: The current user.
    **Returns**:
        - UserGoal: The created goal.
    '''
    catalog = catalogs_repo.get_catalog_goal(conn, body.catalog_id)
    if not catalog:
        raise not_found("Catalog goal not found.")

    if goals_repo.has_catalog(conn, user.id, body.catalog_id):
        raise goal_already_added()

    goal_id = new_id("g")
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
        "sortOrder": goals_repo.count_for_user(conn, user.id),
    }
    goals_repo.create(conn, user.id, goal)
    recompute_progress(conn, user.id, goal_id)
    return goals_repo.get(conn, user.id, goal_id)


@router.get("/goals/{goal_id}", response_model=UserGoal)
def get_goal(
    goal_id: str,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    '''
    Get a goal for the current user.

    **Args**:
        - goal_id: str: The ID of the goal to get.
        - user: UserRecord: The current user.
    **Returns**:
        - UserGoal: The goal.
    '''
    goal = goals_repo.get(conn, user.id, goal_id)
    if not goal:
        raise not_found("Goal not found.")
    return goal


@router.patch("/goals/{goal_id}", response_model=UserGoal)
def update_goal(
    goal_id: str,
    body: UpdateGoalRequest,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    '''
    Update a goal for the current user.

    **Args**:
        - goal_id: str: The ID of the goal to update.
        - body: UpdateGoalRequest: The request body containing the status and confidence of the goal.
        - user: UserRecord: The current user.
    **Returns**:
        - UserGoal: The updated goal.
    '''
    if not goals_repo.exists(conn, user.id, goal_id):
        raise not_found("Goal not found.")

    if body.status is not None:
        goals_repo.set_status(conn, user.id, goal_id, body.status)
    if body.confidence is not None:
        for value in body.confidence.values():
            if not 1 <= value <= 5:
                raise validation_error("Confidence must be between 1 and 5.", "confidence")
        goals_repo.update_confidence(conn, goal_id, body.confidence)

    recompute_progress(conn, user.id, goal_id)
    return goals_repo.get(conn, user.id, goal_id)


@router.delete("/goals/{goal_id}", status_code=204, response_model=None)
def delete_goal(
    goal_id: str,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> None:
    '''
    Delete a goal for the current user.

    **Args**:
        - goal_id: str: The ID of the goal to delete.
        - user: UserRecord: The current user.
    **Returns**:
        - None: The response is empty.
    '''
    if not goals_repo.exists(conn, user.id, goal_id):
        raise not_found("Goal not found.")

    # Deleting the goal cascades (in DB) to its tracking, saved jobs, applications,
    # interview reviews and mock sessions -- all repository-owned now.
    goals_repo.delete(conn, user.id, goal_id)
    goals_repo.repack_sort_order(conn, user.id)


@router.put("/goals/order", response_model=list[UserGoal])
def reorder_goals(
    body: ReorderGoalsRequest,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[dict]:
    '''
    Reorder the goals for the current user.

    **Args**:
        - body: ReorderGoalsRequest: The request body containing the IDs of the goals to reorder.
        - user: UserRecord: The current user.
    **Returns**:
        - list[UserGoal]: The list of goals for the current user, sorted by sortOrder.
    '''
    current_ids = {g["id"] for g in goals_repo.list_for_user(conn, user.id)}
    if set(body.goal_ids) != current_ids:
        raise validation_error("goalIds must include every goal exactly once.", "goalIds")
    goals_repo.reorder(conn, user.id, body.goal_ids)
    return goals_repo.list_for_user(conn, user.id)
