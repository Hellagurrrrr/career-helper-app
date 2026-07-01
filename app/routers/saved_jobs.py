from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.core.errors import not_found, validation_error
from app.db import get_conn
from app.models import UserRecord
from app.repositories import catalogs as catalogs_repo
from app.repositories import goals as goals_repo
from app.repositories import saved_jobs as saved_jobs_repo
from app.schemas.jobs import JobListing, SaveJobRequest

router = APIRouter(prefix="/saved-jobs", tags=["saved-jobs"])


@router.get("", response_model=list[JobListing])
def list_saved_jobs(
    goal_id: str = Query(..., alias="goalId"),
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[dict]:
    """
    List the saved jobs for a goal.
    **Parameters**:
        - goal_id: str: The ID of the goal.
        - user: UserRecord: The current user.
    **Returns**:
        - list[dict]: The list of saved jobs.
    """
    if not goals_repo.exists(conn, user.id, goal_id):
        raise not_found("Goal not found.")
    job_ids = saved_jobs_repo.list_job_ids(conn, user.id, goal_id)
    return [j for jid in job_ids if (j := catalogs_repo.get_job(conn, jid))]


@router.put("/{job_id}", response_model=list[JobListing])
def save_job(
    job_id: str,
    body: SaveJobRequest,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[dict]:
    """
    Save a job for a goal.
    **Parameters**:
        - job_id: str: The ID of the job.
        - body: SaveJobRequest: The request body.
        - user: UserRecord: The current user.
    **Returns**:
        - list[dict]: The list of saved jobs.
    """
    if not goals_repo.exists(conn, user.id, body.goal_id):
        raise validation_error("Goal not found.", "goalId")
    if not catalogs_repo.get_job(conn, job_id):
        raise not_found("Job not found.")
    saved_jobs_repo.add(conn, user.id, body.goal_id, job_id)
    job_ids = saved_jobs_repo.list_job_ids(conn, user.id, body.goal_id)
    return [j for jid in job_ids if (j := catalogs_repo.get_job(conn, jid))]


@router.delete("/{job_id}", status_code=204, response_model=None)
def unsave_job(
    job_id: str,
    goal_id: str = Query(..., alias="goalId"),
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> None:
    """
    Unsave a job for a goal.
    **Parameters**:
        - job_id: str: The ID of the job.
        - goal_id: str: The ID of the goal.
        - user: UserRecord: The current user.
    **Returns**:
        - None: The response body.
    """
    if not saved_jobs_repo.remove(conn, user.id, goal_id, job_id):
        raise not_found("Saved job not found.")
