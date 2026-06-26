from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.core.errors import not_found
from app.db import get_conn
from app.repositories import goals as goals_repo
from app.repositories import profiles as profiles_repo
from app.schemas.alumni import AlumniProfile
from app.services import mock_match
from app.services.store import UserRecord, store

router = APIRouter(prefix="/alumni", tags=["alumni"])


@router.get("", response_model=list[AlumniProfile])
def list_alumni(
    goal_id: str | None = Query(default=None, alias="goalId"),
    q: str | None = Query(default=None),
    expertise: str | None = Query(default=None),
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[dict]:
    '''
    List the alumni for a goal.
    **Parameters**:
        - goal_id: str | None: The ID of the goal.
        - q: str | None: The query to filter by.
        - expertise: str | None: The expertise to filter by.
        - user: UserRecord: The current user.
    **Returns**:
        - list[dict]: The list of alumni.
    '''
    alumni = list(store.alumni)
    if expertise:
        needle = expertise.strip().lower()
        alumni = [a for a in alumni if any(needle in e.lower() for e in a.get("expertise", []))]
    if q:
        needle = q.strip().lower()
        alumni = [
            a
            for a in alumni
            if needle in a["role"].lower()
            or needle in a["company"].lower()
            or any(needle in t.lower() for t in a.get("topics", []))
            or any(needle in e.lower() for e in a.get("expertise", []))
        ]

    profile = profiles_repo.get(conn, user.id)
    user_goals = goals_repo.list_for_user(conn, user.id)
    catalog_ids = {g["catalogId"] for g in user_goals}
    if goal_id:
        match = goals_repo.get(conn, user.id, goal_id)
        if match:
            catalog_ids = {match["catalogId"]}
    return mock_match.sort_alumni(profile, catalog_ids, alumni)


@router.get("/{alumni_id}", response_model=AlumniProfile)
def get_alumni(alumni_id: str, user: UserRecord = Depends(get_current_user)) -> dict:
    '''
    Get an alumni profile.
    **Parameters**:
        - alumni_id: str: The ID of the alumni.
        - user: UserRecord: The current user.
    **Returns**:
        - dict: The alumni profile.
    '''
    alum = store.get_alumni(alumni_id)
    if not alum:
        raise not_found("Profile not found.")
    return alum
