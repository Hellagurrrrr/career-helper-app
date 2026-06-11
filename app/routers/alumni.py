from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.core.errors import not_found
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
) -> list[dict]:
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

    profile = store.profiles.get(user.id)
    user_goals = store.goals.get(user.id, {}).values()
    catalog_ids = {g["catalogId"] for g in user_goals}
    if goal_id and goal_id in store.goals.get(user.id, {}):
        catalog_ids = {store.goals[user.id][goal_id]["catalogId"]}
    return mock_match.sort_alumni(profile, catalog_ids, alumni)


@router.get("/{alumni_id}", response_model=AlumniProfile)
def get_alumni(alumni_id: str, user: UserRecord = Depends(get_current_user)) -> dict:
    alum = store.get_alumni(alumni_id)
    if not alum:
        raise not_found("Profile not found.")
    return alum
