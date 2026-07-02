from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.core.errors import meeting_already_pending, not_found, validation_error
from app.core.security import new_id, now_ms
from app.db import get_conn
from app.models import UserRecord
from app.repositories import catalogs as catalogs_repo
from app.repositories import meetings as meetings_repo
from app.schemas.alumni import CreateMeetingRequest, MeetingRequest, UpdateMeetingRequest
from app.services import notifications_service

router = APIRouter(prefix="/meetings", tags=["meetings"])

_MIN_MESSAGE_LEN = 20  # use-case AD-04


@router.get("", response_model=list[MeetingRequest])
def list_meetings(
    alumni_id: str | None = Query(default=None, alias="alumniId"),
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[dict]:
    """List the user's meetings newest first, optionally filtered by alumni."""
    return meetings_repo.list_for_user(conn, user.id, alumni_id)


@router.post("", response_model=MeetingRequest, status_code=201)
def create_meeting(
    body: CreateMeetingRequest,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    """Request a coffee chat with an alumni; 409 if one is already pending with them."""
    alum = catalogs_repo.get_alumni(conn, body.alumni_id)
    if not alum:
        raise validation_error("Alumni not found.", "alumniId")
    if not body.topic.strip():
        raise validation_error("Please choose a topic.", "topic")
    if len(body.message.strip()) < _MIN_MESSAGE_LEN:
        raise validation_error(
            f"Message must be at least {_MIN_MESSAGE_LEN} characters.", "message"
        )

    if meetings_repo.has_pending_with_alumni(conn, user.id, body.alumni_id):
        raise meeting_already_pending()

    meeting = meetings_repo.create(
        conn,
        meeting_id=new_id("mtg"),
        user_id=user.id,
        alumni_id=body.alumni_id,
        topic=body.topic.strip(),
        message=body.message.strip(),
        preferred_times=body.preferred_times,
        submitted_at=now_ms(),
    )

    notifications_service.push(
        user.id,
        type="meeting",
        severity="info",
        title="Coffee chat requested",
        body=f"Your request to {alum['firstName']} {alum['lastInitial']}. was sent.",
        link="/alumni?tab=requests",
        dedup_key=f"meeting-created:{meeting['id']}",
    )
    return meeting


@router.patch("/{meeting_id}", response_model=MeetingRequest)
def update_meeting(
    meeting_id: str,
    body: UpdateMeetingRequest,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    """Update a meeting's status; completing it stamps completed_at and notifies the user."""
    # Only set completed_at when transitioning to "completed"; leave it untouched
    # otherwise (matches prior behavior).
    if body.status == "completed":
        meeting = meetings_repo.set_status(
            conn, user.id, meeting_id, body.status, completed_at=now_ms()
        )
    else:
        meeting = meetings_repo.set_status(conn, user.id, meeting_id, body.status)

    if meeting is None:
        raise not_found("Meeting request not found.")

    if body.status == "completed":
        alum = catalogs_repo.get_alumni(conn, meeting["alumni_id"]) or {}
        notifications_service.push(
            user.id,
            type="meeting",
            severity="success",
            title="Coffee chat completed",
            body=f"Marked your chat with {alum.get('firstName', 'an alum')} as completed.",
            link="/alumni?tab=requests",
            dedup_key=f"meeting-completed:{meeting_id}",
        )
    return meeting
