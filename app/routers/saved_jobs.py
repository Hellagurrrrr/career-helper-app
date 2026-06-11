from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.core.errors import not_found, validation_error
from app.schemas.jobs import JobListing, SaveJobRequest
from app.services.store import UserRecord, store

router = APIRouter(prefix="/saved-jobs", tags=["saved-jobs"])


@router.get("", response_model=list[JobListing])
def list_saved_jobs(
    goal_id: str = Query(..., alias="goalId"),
    user: UserRecord = Depends(get_current_user),
) -> list[dict]:
    if goal_id not in store.goals.get(user.id, {}):
        raise not_found("Goal not found.")
    job_ids = store.saved_jobs.get(user.id, {}).get(goal_id, set())
    return [store.get_job(jid) for jid in job_ids if store.get_job(jid)]


@router.put("/{job_id}", response_model=list[JobListing])
def save_job(
    job_id: str,
    body: SaveJobRequest,
    user: UserRecord = Depends(get_current_user),
) -> list[dict]:
    if body.goal_id not in store.goals.get(user.id, {}):
        raise validation_error("Goal not found.", "goalId")
    if not store.get_job(job_id):
        raise not_found("Job not found.")
    by_goal = store.saved_jobs.setdefault(user.id, {})
    saved = by_goal.setdefault(body.goal_id, set())
    saved.add(job_id)
    return [store.get_job(jid) for jid in saved if store.get_job(jid)]


@router.delete("/{job_id}", status_code=204, response_model=None)
def unsave_job(
    job_id: str,
    goal_id: str = Query(..., alias="goalId"),
    user: UserRecord = Depends(get_current_user),
) -> None:
    saved = store.saved_jobs.get(user.id, {}).get(goal_id)
    if not saved or job_id not in saved:
        raise not_found("Saved job not found.")
    saved.discard(job_id)
