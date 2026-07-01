from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.core.errors import not_found
from app.core.pagination import paginate
from app.db import get_conn
from app.models import UserRecord
from app.repositories import catalogs as catalogs_repo
from app.repositories import profiles as profiles_repo
from app.schemas.jobs import JobDetail, JobListPage
from app.services import mock_match

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=JobListPage)
def list_jobs(
    catalog_goal_id: str | None = Query(default=None, alias="catalogGoalId"),
    partner: bool | None = Query(default=None),
    exclusive: bool | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    """
    List jobs.

    **Args**:
        - catalog_goal_id: str | None: The ID of the catalog goal to filter by.
        - partner: bool | None: Whether to filter by partner.
        - exclusive: bool | None: Whether to filter by exclusive.
        - q: str | None: The query to filter by.
    **Returns**:
        - list[Job]: The list of jobs.
    """
    jobs = catalogs_repo.list_jobs(conn)
    if catalog_goal_id is not None:
        jobs = [j for j in jobs if j["catalogGoalId"] == catalog_goal_id]
    if partner is not None:
        jobs = [j for j in jobs if j.get("partner", False) == partner]
    if exclusive is not None:
        jobs = [j for j in jobs if j.get("exclusive", False) == exclusive]
    if q:
        needle = q.strip().lower()
        jobs = [
            j
            for j in jobs
            if needle in j["title"].lower()
            or needle in j["company"].lower()
            or any(needle in s.lower() for s in j.get("skills", []))
        ]
    # Attach the profile-vs-job match % per job (same score as the detail view),
    # so the list cards can show it instead of "--".
    profile_skills = (profiles_repo.get(conn, user.id) or {}).get("skills", [])
    jobs = [
        {**j, "matchScore": mock_match.match_score(profile_skills, j.get("skills", []))}
        for j in jobs
    ]
    return paginate(jobs, limit, cursor)


@router.get("/{job_id}", response_model=JobDetail)
def get_job(
    job_id: str,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    """
    Get a job.

    **Args**:
        - job_id: str: The ID of the job to get.
        - user: UserRecord: The current user.
    **Returns**:
        - JobDetail: The job.
    """
    job = catalogs_repo.get_job(conn, job_id)
    if not job:
        raise not_found("Job not found.")
    profile = profiles_repo.get(conn, user.id) or {}
    score = mock_match.match_score(profile.get("skills", []), job.get("skills", []))
    return {**job, "matchScore": score}
