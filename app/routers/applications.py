from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.core.errors import (
    APIError,
    already_applied,
    not_exclusive_job,
    not_found,
    validation_error,
)
from app.core.security import new_id, now_ms
from app.db import get_conn
from app.repositories import applications as applications_repo
from app.repositories import catalogs as catalogs_repo
from app.repositories import goals as goals_repo
from app.schemas.applications import (
    ApplicationListResponse,
    CreateApplicationRequest,
    JobApplication,
    UpdateApplicationRequest,
)
from app.services import applications_service
from app.services.store import UserRecord

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("", response_model=ApplicationListResponse)
def list_applications(
    goal_id: str | None = Query(default=None, alias="goalId"),
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    '''
    List the applications for a goal.
    **Parameters**:
        - goal_id: str | None: The ID of the goal.
        - user: UserRecord: The current user.
    **Returns**:
        - dict: The list of applications.
    '''
    apps = applications_repo.list_for_user(conn, user.id)
    # Advance partner pipelines before reporting (use-case APP-05).
    for app in apps:
        applications_service.advance_partner(conn, user.id, app)
    if goal_id is not None:
        apps = [a for a in apps if a["goalId"] == goal_id]
    items = [applications_service.with_counts(conn, user.id, a) for a in apps]
    summary = applications_service.summarize(apps)
    return {"items": items, "summary": summary}


@router.post("", response_model=JobApplication, status_code=201)
def create_application(
    body: CreateApplicationRequest,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    '''
    Create an application for a goal.
    **Parameters**:
        - body: CreateApplicationRequest: The request body.
        - user: UserRecord: The current user.
    **Returns**:
        - dict: The application.
    '''
    if not goals_repo.exists(conn, user.id, body.goal_id):
        raise validation_error("Goal not found.", "goalId")
    job = catalogs_repo.get_job(conn, body.job_id)
    if not job:
        raise validation_error("Job not found.", "jobId")
    if body.kind == "partner" and not job.get("exclusive", False):
        raise not_exclusive_job()

    if applications_repo.has_job(conn, user.id, body.job_id):
        raise already_applied()

    app_id = new_id("app")
    app = {
        "id": app_id,
        "kind": body.kind,
        "goalId": body.goal_id,
        "jobId": body.job_id,
        "title": job["title"],
        "company": job["company"],
        "submittedAt": now_ms(),
        "partnerStatus": "referral_sent" if body.kind == "partner" else None,
        "manualStatus": "applied" if body.kind == "standard" else None,
    }
    applications_repo.create(conn, user.id, app)
    return applications_service.with_counts(conn, user.id, app)


@router.patch("/{application_id}", response_model=JobApplication)
def update_application(
    application_id: str,
    body: UpdateApplicationRequest,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    '''
    Update an application for a goal.
    **Parameters**:
        - application_id: str: The ID of the application.
        - body: UpdateApplicationRequest: The request body.
        - user: UserRecord: The current user.
    **Returns**:
        - dict: The application.
    '''
    app = applications_repo.get(conn, user.id, application_id)
    if not app:
        raise not_found("Application not found.")
    if app["kind"] == "partner":
        raise APIError(
            "VALIDATION_ERROR",
            422,
            "Partner application status is managed automatically.",
            {"field": "manualStatus"},
        )
    applications_repo.set_manual_status(conn, user.id, application_id, body.manual_status)
    app["manualStatus"] = body.manual_status
    return applications_service.with_counts(conn, user.id, app)


@router.delete("/{application_id}", status_code=204, response_model=None)
def delete_application(
    application_id: str,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> None:
    '''
    Delete an application for a goal.
    **Parameters**:
        - application_id: str: The ID of the application.
        - user: UserRecord: The current user.
    **Returns**:
        - None: The response body.
    '''
    # Reviews and mock sessions cascade via FK.
    if not applications_repo.delete(conn, user.id, application_id):
        raise not_found("Application not found.")
