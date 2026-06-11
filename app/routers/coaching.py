from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.errors import (
    file_too_large,
    mock_session_incomplete,
    not_found,
    unsupported_audio_format,
    validation_error,
)
from app.core.security import new_id, now_ms
from app.schemas.applications import JobApplication
from app.schemas.coaching import (
    CoachingSummary,
    InterviewReview,
    MockInterviewSession,
    MockStartResponse,
    MockTurnRequest,
    MockTurnResponse,
    ReviewCreatedResponse,
    ReviewStatusResponse,
)
from app.services import applications_service, mock_ai
from app.services.store import UserRecord, store

router = APIRouter(tags=["ai-coaching"])

_ALLOWED_AUDIO_EXT = (".mp3", ".wav", ".m4a", ".webm")


def _get_app_or_404(user_id: str, application_id: str) -> dict[str, Any]:
    app = store.applications.get(user_id, {}).get(application_id)
    if not app:
        raise not_found("Application not found.")
    return app


def _context(user_id: str, app: dict[str, Any]) -> dict[str, Any]:
    job = store.get_job(app["jobId"]) or {}
    goal = store.goals.get(user_id, {}).get(app["goalId"]) or {}
    return {
        "jobTitle": app["title"],
        "company": app["company"],
        "goalTitle": goal.get("title"),
        "skills": job.get("skills", []),
    }


# ---------------------------------------------------------------------------
# Page-level (api-design 9.1)
# ---------------------------------------------------------------------------
@router.get("/ai-coaching/summary", response_model=CoachingSummary)
def coaching_summary(user: UserRecord = Depends(get_current_user)) -> dict:
    apps = store.applications.get(user.id, {})
    review_count = sum(
        sum(1 for r in rs if r.get("status") == "complete")
        for rs in store.reviews.get(user.id, {}).values()
    )
    mock_count = sum(len(ms) for ms in store.mocks.get(user.id, {}).values())
    return {
        "applicationCount": len(apps),
        "reviewCount": review_count,
        "mockCount": mock_count,
    }


@router.get("/ai-coaching/applications", response_model=list[JobApplication])
def coaching_applications(user: UserRecord = Depends(get_current_user)) -> list[dict]:
    apps = list(store.applications.get(user.id, {}).values())
    for app in apps:
        applications_service.advance_partner(user.id, app)
    apps_sorted = sorted(apps, key=lambda a: a["submittedAt"], reverse=True)
    return [applications_service.with_counts(user.id, a) for a in apps_sorted]


# ---------------------------------------------------------------------------
# Interview reviews (api-design 9.4 / 9.5)
# ---------------------------------------------------------------------------
@router.get("/applications/{application_id}/interview-reviews", response_model=list[InterviewReview])
def list_reviews(application_id: str, user: UserRecord = Depends(get_current_user)) -> list[dict]:
    _get_app_or_404(user.id, application_id)
    reviews = store.reviews.get(user.id, {}).get(application_id, [])
    completed = [r for r in reviews if r.get("status") == "complete"]
    return sorted(completed, key=lambda r: r["uploadedAt"], reverse=True)


@router.post(
    "/applications/{application_id}/interview-reviews",
    response_model=ReviewCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_review(
    application_id: str,
    file: UploadFile = File(...),
    user: UserRecord = Depends(get_current_user),
) -> dict:
    _get_app_or_404(user.id, application_id)
    name = (file.filename or "").lower()
    if not name.endswith(_ALLOWED_AUDIO_EXT):
        raise unsupported_audio_format()
    contents = file.file.read()
    if len(contents) > settings.audio_max_bytes:
        raise file_too_large("File is too large. Maximum size is 25 MB.")

    review_id = new_id("ir")
    review = {
        "id": review_id,
        "applicationId": application_id,
        "fileName": file.filename or "audio",
        "uploadedAt": now_ms(),
        "durationSec": None,
        "transcript": "",
        "overallSummary": "",
        "dimensions": [],
        "improvementAdvice": "",
        "status": "transcribing",
        "polls": 0,
    }
    store.reviews.setdefault(user.id, {}).setdefault(application_id, []).append(review)
    return {"id": review_id, "applicationId": application_id, "status": "transcribing"}


@router.get(
    "/applications/{application_id}/interview-reviews/{review_id}",
    response_model=ReviewStatusResponse,
)
def get_review(
    application_id: str,
    review_id: str,
    user: UserRecord = Depends(get_current_user),
) -> dict:
    _get_app_or_404(user.id, application_id)
    reviews = store.reviews.get(user.id, {}).get(application_id, [])
    review = next((r for r in reviews if r["id"] == review_id), None)
    if not review:
        raise not_found("Review not found.")

    if review["status"] != "complete":
        review["polls"] += 1
        if review["polls"] <= settings.async_processing_polls:
            review["status"] = mock_ai.review_stage(review["polls"])
            return {"id": review_id, "applicationId": application_id, "status": review["status"]}
        # Finalize analysis.
        analysis = mock_ai.mock_review_analysis(review["fileName"])
        review.update(analysis)
        review["durationSec"] = 180
        review["status"] = "complete"

    return {
        "id": review_id,
        "applicationId": application_id,
        "status": "complete",
        "review": InterviewReview.model_validate(review),
    }


@router.delete(
    "/applications/{application_id}/interview-reviews/{review_id}",
    status_code=204,
    response_model=None,
)
def delete_review(
    application_id: str,
    review_id: str,
    user: UserRecord = Depends(get_current_user),
) -> None:
    reviews = store.reviews.get(user.id, {}).get(application_id, [])
    idx = next((i for i, r in enumerate(reviews) if r["id"] == review_id), None)
    if idx is None:
        raise not_found("Review not found.")
    reviews.pop(idx)


# ---------------------------------------------------------------------------
# Mock interviews (api-design 9.6)
# ---------------------------------------------------------------------------
def _finalize_mock(session: dict[str, Any]) -> None:
    session["completedAt"] = now_ms()
    session["durationSec"] = max(1, (session["completedAt"] - session["startedAt"]) // 1000)
    session.update(mock_ai.mock_interview_evaluation(session["turns"]))
    session["status"] = "complete"


@router.get(
    "/applications/{application_id}/mock-interviews",
    response_model=list[MockInterviewSession],
)
def list_mocks(application_id: str, user: UserRecord = Depends(get_current_user)) -> list[dict]:
    _get_app_or_404(user.id, application_id)
    sessions = store.mocks.get(user.id, {}).get(application_id, [])
    return sorted(sessions, key=lambda s: s["startedAt"], reverse=True)


@router.post(
    "/applications/{application_id}/mock-interviews",
    response_model=MockStartResponse,
    status_code=201,
)
def start_mock(application_id: str, user: UserRecord = Depends(get_current_user)) -> dict:
    app = _get_app_or_404(user.id, application_id)
    ctx = _context(user.id, app)
    job = store.get_job(app["jobId"]) or {}
    questions = mock_ai.mock_interview_questions(job)

    session_id = new_id("mock")
    ts = now_ms()
    session = {
        "id": session_id,
        "applicationId": application_id,
        "jobTitle": ctx["jobTitle"],
        "company": ctx["company"],
        "goalTitle": ctx["goalTitle"],
        "skills": ctx["skills"],
        "startedAt": ts,
        "completedAt": None,
        "durationSec": None,
        "turns": [
            {"id": new_id("t"), "role": "coach", "text": questions[0], "timestamp": ts}
        ],
        "transcript": "",
        "overallSummary": "",
        "dimensions": [],
        "improvementAdvice": "",
        "questions": questions,
        "currentIndex": 0,
        "status": "in_progress",
    }
    store.mocks.setdefault(user.id, {}).setdefault(application_id, []).append(session)
    return {
        "sessionId": session_id,
        "status": "in_progress",
        "question": questions[0],
        "questionIndex": 0,
        "totalQuestions": len(questions),
    }


@router.post(
    "/applications/{application_id}/mock-interviews/{session_id}/turns",
    response_model=MockTurnResponse,
)
def submit_turn(
    application_id: str,
    session_id: str,
    body: MockTurnRequest,
    user: UserRecord = Depends(get_current_user),
) -> dict:
    _get_app_or_404(user.id, application_id)
    sessions = store.mocks.get(user.id, {}).get(application_id, [])
    session = next((s for s in sessions if s["id"] == session_id), None)
    if not session:
        raise not_found("Mock session not found.")
    if session["status"] == "complete":
        raise validation_error("This mock interview is already complete.")

    user_turns = [t for t in session["turns"] if t["role"] == "user"]

    if body.end:
        if not user_turns:
            raise mock_session_incomplete()
        _finalize_mock(session)
        return {"status": "complete", "session": MockInterviewSession.model_validate(session)}

    if not body.text.strip():
        raise validation_error("Answer text is required.", "text")

    session["turns"].append(
        {"id": new_id("t"), "role": "user", "text": body.text.strip(), "timestamp": now_ms()}
    )
    session["currentIndex"] += 1
    idx = session["currentIndex"]

    if idx < len(session["questions"]):
        question = session["questions"][idx]
        session["turns"].append(
            {"id": new_id("t"), "role": "coach", "text": question, "timestamp": now_ms()}
        )
        return {
            "status": "in_progress",
            "question": question,
            "questionIndex": idx,
            "totalQuestions": len(session["questions"]),
        }

    _finalize_mock(session)
    return {"status": "complete", "session": MockInterviewSession.model_validate(session)}


@router.get(
    "/applications/{application_id}/mock-interviews/{session_id}",
    response_model=MockInterviewSession,
)
def get_mock(
    application_id: str,
    session_id: str,
    user: UserRecord = Depends(get_current_user),
) -> dict:
    _get_app_or_404(user.id, application_id)
    sessions = store.mocks.get(user.id, {}).get(application_id, [])
    session = next((s for s in sessions if s["id"] == session_id), None)
    if not session:
        raise not_found("Mock session not found.")
    return session


@router.delete(
    "/applications/{application_id}/mock-interviews/{session_id}",
    status_code=204,
    response_model=None,
)
def delete_mock(
    application_id: str,
    session_id: str,
    user: UserRecord = Depends(get_current_user),
) -> None:
    sessions = store.mocks.get(user.id, {}).get(application_id, [])
    idx = next((i for i, s in enumerate(sessions) if s["id"] == session_id), None)
    if idx is None:
        raise not_found("Mock session not found.")
    sessions.pop(idx)
