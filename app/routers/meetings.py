from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.core.errors import meeting_already_pending, not_found, validation_error
from app.core.security import new_id, now_ms
from app.schemas.alumni import CreateMeetingRequest, MeetingRequest, UpdateMeetingRequest
from app.services import notifications_service
from app.services.store import UserRecord, store

router = APIRouter(prefix="/meetings", tags=["meetings"])

_MIN_MESSAGE_LEN = 20  # use-case AD-04


@router.get("", response_model=list[MeetingRequest])
def list_meetings(
    alumni_id: str | None = Query(default=None, alias="alumniId"),
    user: UserRecord = Depends(get_current_user),
) -> list[dict]:
    meetings = list(store.meetings.get(user.id, {}).values())
    if alumni_id is not None:
        meetings = [m for m in meetings if m["alumniId"] == alumni_id]
    return sorted(meetings, key=lambda m: m["submittedAt"], reverse=True)


@router.post("", response_model=MeetingRequest, status_code=201)
def create_meeting(body: CreateMeetingRequest, user: UserRecord = Depends(get_current_user)) -> dict:
    alum = store.get_alumni(body.alumni_id)
    if not alum:
        raise validation_error("Alumni not found.", "alumniId")
    if not body.topic.strip():
        raise validation_error("Please choose a topic.", "topic")
    if len(body.message.strip()) < _MIN_MESSAGE_LEN:
        raise validation_error(
            f"Message must be at least {_MIN_MESSAGE_LEN} characters.", "message"
        )

    bucket = store.meetings.setdefault(user.id, {})
    if any(m["alumniId"] == body.alumni_id and m["status"] == "pending" for m in bucket.values()):
        raise meeting_already_pending()

    meeting_id = new_id("mtg")
    meeting = {
        "id": meeting_id,
        "alumniId": body.alumni_id,
        "topic": body.topic.strip(),
        "message": body.message.strip(),
        "preferredTimes": body.preferred_times,
        "submittedAt": now_ms(),
        "status": "pending",
        "completedAt": None,
    }
    bucket[meeting_id] = meeting

    notifications_service.push(
        user.id,
        type="meeting",
        severity="info",
        title="Coffee chat requested",
        body=f"Your request to {alum['firstName']} {alum['lastInitial']}. was sent.",
        link="/alumni?tab=requests",
        dedup_key=f"meeting-created:{meeting_id}",
    )
    return meeting


@router.patch("/{meeting_id}", response_model=MeetingRequest)
def update_meeting(
    meeting_id: str,
    body: UpdateMeetingRequest,
    user: UserRecord = Depends(get_current_user),
) -> dict:
    meeting = store.meetings.get(user.id, {}).get(meeting_id)
    if not meeting:
        raise not_found("Meeting request not found.")

    meeting["status"] = body.status
    if body.status == "completed":
        meeting["completedAt"] = now_ms()
        alum = store.get_alumni(meeting["alumniId"]) or {}
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
