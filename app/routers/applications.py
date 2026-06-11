from __future__ import annotations

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
from app.schemas.applications import (
    ApplicationListResponse,
    CreateApplicationRequest,
    JobApplication,
    UpdateApplicationRequest,
)
from app.services import applications_service
from app.services.store import UserRecord, store

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("", response_model=ApplicationListResponse)
def list_applications(
    goal_id: str | None = Query(default=None, alias="goalId"),
    user: UserRecord = Depends(get_current_user),
) -> dict:
    apps = list(store.applications.get(user.id, {}).values())
    # Advance partner pipelines before reporting (use-case APP-05).
    for app in apps:
        applications_service.advance_partner(user.id, app)
    if goal_id is not None:
        apps = [a for a in apps if a["goalId"] == goal_id]
    apps_sorted = sorted(apps, key=lambda a: a["submittedAt"], reverse=True)
    items = [applications_service.with_counts(user.id, a) for a in apps_sorted]
    summary = applications_service.summarize(apps)
    return {"items": items, "summary": summary}


@router.post("", response_model=JobApplication, status_code=201)
def create_application(
    body: CreateApplicationRequest,
    user: UserRecord = Depends(get_current_user),
) -> dict:
    if body.goal_id not in store.goals.get(user.id, {}):
        raise validation_error("Goal not found.", "goalId")
    job = store.get_job(body.job_id)
    if not job:
        raise validation_error("Job not found.", "jobId")
    if body.kind == "partner" and not job.get("exclusive", False):
        raise not_exclusive_job()

    bucket = store.applications.setdefault(user.id, {})
    if any(a["jobId"] == body.job_id for a in bucket.values()):
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
    bucket[app_id] = app
    return applications_service.with_counts(user.id, app)


@router.patch("/{application_id}", response_model=JobApplication)
def update_application(
    application_id: str,
    body: UpdateApplicationRequest,
    user: UserRecord = Depends(get_current_user),
) -> dict:
    app = store.applications.get(user.id, {}).get(application_id)
    if not app:
        raise not_found("Application not found.")
    if app["kind"] == "partner":
        raise APIError(
            "VALIDATION_ERROR",
            422,
            "Partner application status is managed automatically.",
            {"field": "manualStatus"},
        )
    app["manualStatus"] = body.manual_status
    return applications_service.with_counts(user.id, app)


@router.delete("/{application_id}", status_code=204, response_model=None)
def delete_application(application_id: str, user: UserRecord = Depends(get_current_user)) -> None:
    bucket = store.applications.get(user.id, {})
    if application_id not in bucket:
        raise not_found("Application not found.")
    bucket.pop(application_id, None)
    store.reviews.get(user.id, {}).pop(application_id, None)
    store.mocks.get(user.id, {}).pop(application_id, None)
