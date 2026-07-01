from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Response, UploadFile, status

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.errors import (
    file_too_large,
    mock_session_incomplete,
    not_found,
    speech_not_supported,
    unsupported_audio_format,
    validation_error,
)
from app.core.security import new_id, now_ms
from app.db import get_conn, get_connection
from app.models import UserRecord
from app.repositories import applications as applications_repo
from app.repositories import catalogs as catalogs_repo
from app.repositories import goals as goals_repo
from app.repositories import mocks as mocks_repo
from app.repositories import profiles as profiles_repo
from app.repositories import reviews as reviews_repo
from app.repositories import tts_cache as tts_cache_repo
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
from app.services import ai_service, applications_service

router = APIRouter(tags=["ai-coaching"])

_ALLOWED_AUDIO_EXT = (".mp3", ".wav", ".m4a", ".webm")


def _get_app_or_404(conn: sqlite3.Connection, user_id: str, application_id: str) -> dict[str, Any]:
    app = applications_repo.get(conn, user_id, application_id)
    if not app:
        raise not_found("Application not found.")
    return app


def _context(user_id: str, app: dict[str, Any]) -> dict[str, Any]:
    conn = get_connection()
    job = catalogs_repo.get_job(conn, app["jobId"]) or {}
    goal = goals_repo.get(conn, user_id, app["goalId"]) or {}
    return {
        "jobTitle": app["title"],
        "company": app["company"],
        "goalTitle": goal.get("title"),
        "skills": job.get("skills", []),
    }


def _run_review_analysis(review: dict[str, Any], audio_bytes: bytes, filename: str) -> None:
    """Real-AI background job: transcribe the recording, then score the transcript.

    Runs outside a request, so it persists each observable step via the shared
    connection.
    """
    conn = get_connection()
    try:
        review["status"] = "transcribing"
        reviews_repo.save(conn, review)
        conn.commit()
        transcript = ai_service.transcribe(audio_bytes, filename)
        review["transcript"] = transcript
        review["status"] = "scoring"
        reviews_repo.save(conn, review)
        conn.commit()
        analysis = ai_service.analyze_transcript(transcript)
        review["overallSummary"] = analysis["overallSummary"]
        review["dimensions"] = analysis["dimensions"]
        review["improvementAdvice"] = analysis["improvementAdvice"]
        review["status"] = "complete"
        reviews_repo.save(conn, review)
        conn.commit()
    except Exception as exc:  # noqa: BLE001 - surface failure to the poller
        review["status"] = "failed"
        review["error"] = str(exc)
        reviews_repo.save(conn, review)
        conn.commit()


# ---------------------------------------------------------------------------
# Page-level (api-design 9.1)
# ---------------------------------------------------------------------------
@router.get("/ai-coaching/summary", response_model=CoachingSummary)
def coaching_summary(
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    """Return the coaching page counters (applications, completed reviews, mock sessions)."""
    return {
        "applicationCount": applications_repo.count_for_user(conn, user.id),
        "reviewCount": reviews_repo.count_complete_for_user(conn, user.id),
        "mockCount": mocks_repo.count_for_user(conn, user.id),
    }


@router.get("/ai-coaching/applications", response_model=list[JobApplication])
def coaching_applications(
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[dict]:
    """List the user's applications (partner pipelines advanced) for the coaching page."""
    apps = applications_repo.list_for_user(conn, user.id)
    for app in apps:
        applications_service.advance_partner(conn, user.id, app)
    return [applications_service.with_counts(conn, user.id, a) for a in apps]


# ---------------------------------------------------------------------------
# Interview reviews (api-design 9.4 / 9.5)
# ---------------------------------------------------------------------------
@router.get(
    "/applications/{application_id}/interview-reviews", response_model=list[InterviewReview]
)
def list_reviews(
    application_id: str,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[dict]:
    """List the completed interview reviews for an application."""
    _get_app_or_404(conn, user.id, application_id)
    reviews = reviews_repo.list_for_app(conn, user.id, application_id)
    return [r for r in reviews if r.get("status") == "complete"]


@router.post(
    "/applications/{application_id}/interview-reviews",
    response_model=ReviewCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_review(
    application_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    """Upload interview audio and start async transcription + scoring; poll get_review for the result."""
    _get_app_or_404(conn, user.id, application_id)
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
    reviews_repo.create(conn, user.id, review)
    if ai_service.real_enabled():
        # Real AI: transcribe + score in the background; get_review reports status.
        background_tasks.add_task(_run_review_analysis, review, contents, review["fileName"])
    return {"id": review_id, "applicationId": application_id, "status": "transcribing"}


@router.get(
    "/applications/{application_id}/interview-reviews/{review_id}",
    response_model=ReviewStatusResponse,
)
def get_review(
    application_id: str,
    review_id: str,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    """Poll an interview review; returns status while processing and the full review once complete."""
    _get_app_or_404(conn, user.id, application_id)
    review = reviews_repo.get(conn, user.id, review_id)
    if not review or review["applicationId"] != application_id:
        raise not_found("Review not found.")

    if ai_service.real_enabled():
        # Real AI: the background task owns the state machine; just report it.
        if review["status"] != "complete":
            return {"id": review_id, "applicationId": application_id, "status": review["status"]}
    else:
        # Mock: simulate the analysis pipeline via the poll counter.
        if review["status"] != "complete":
            review["polls"] += 1
            if review["polls"] <= settings.async_processing_polls:
                review["status"] = ai_service.review_stage(review["polls"])
                reviews_repo.save(conn, review)
                return {
                    "id": review_id,
                    "applicationId": application_id,
                    "status": review["status"],
                }
            analysis = ai_service.mock_review_analysis(review["fileName"])
            review.update(analysis)
            review["durationSec"] = 180
            review["status"] = "complete"
            reviews_repo.save(conn, review)

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
    conn: sqlite3.Connection = Depends(get_conn),
) -> None:
    """Delete an interview review; 404 if unknown."""
    if not reviews_repo.delete(conn, user.id, application_id, review_id):
        raise not_found("Review not found.")


# ---------------------------------------------------------------------------
# Mock interviews (api-design 9.6)
# ---------------------------------------------------------------------------
def _build_transcript(turns: list[dict[str, Any]]) -> str:
    return "\n".join(f"{t['role']}: {t['text']}" for t in turns)


def _run_mock_scoring(session: dict[str, Any]) -> None:
    """Real-AI background job: score a finished mock interview transcript."""
    conn = get_connection()
    try:
        transcript = _build_transcript(session["turns"])
        analysis = ai_service.analyze_transcript(transcript)
        session["transcript"] = transcript
        session["overallSummary"] = analysis["overallSummary"]
        session["dimensions"] = analysis["dimensions"]
        session["improvementAdvice"] = analysis["improvementAdvice"]
        session["status"] = "complete"
    except Exception as exc:  # noqa: BLE001 - surface failure to the poller
        session["status"] = "failed"
        session["error"] = str(exc)
    mocks_repo.save(conn, session)
    conn.commit()


def _finalize_mock(session: dict[str, Any], background_tasks: BackgroundTasks) -> None:
    session["completedAt"] = now_ms()
    session["durationSec"] = max(1, (session["completedAt"] - session["startedAt"]) // 1000)
    if ai_service.real_enabled():
        # Scoring is a real LLM call -> run it in the background; client polls
        # GET .../mock-interviews/{id} until dimensions are populated.
        session["status"] = "scoring"
        background_tasks.add_task(_run_mock_scoring, session)
    else:
        session.update(ai_service.mock_interview_evaluation(session["turns"]))
        session["status"] = "complete"


def _finalize_response(
    session: dict[str, Any], background_tasks: BackgroundTasks
) -> dict[str, Any]:
    _finalize_mock(session, background_tasks)
    return {"status": session["status"], "session": MockInterviewSession.model_validate(session)}


def _process_turn(
    session: dict[str, Any],
    text: str,
    end: bool,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Shared logic for text and voice answers."""
    if session["status"] not in ("in_progress",):
        raise validation_error("This mock interview is already complete.")

    user_turns = [t for t in session["turns"] if t["role"] == "user"]

    if end:
        if not user_turns:
            raise mock_session_incomplete()
        return _finalize_response(session, background_tasks)

    if not text.strip():
        raise validation_error("Answer text is required.", "text")

    session["turns"].append(
        {"id": new_id("t"), "role": "user", "text": text.strip(), "timestamp": now_ms()}
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

    return _finalize_response(session, background_tasks)


def _find_mock(
    conn: sqlite3.Connection, user_id: str, application_id: str, session_id: str
) -> dict[str, Any]:
    session = mocks_repo.get(conn, user_id, session_id)
    if not session or session["applicationId"] != application_id:
        raise not_found("Mock session not found.")
    return session


@router.get(
    "/applications/{application_id}/mock-interviews",
    response_model=list[MockInterviewSession],
)
def list_mocks(
    application_id: str,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[dict]:
    """List the mock interview sessions for an application."""
    _get_app_or_404(conn, user.id, application_id)
    return mocks_repo.list_for_app(conn, user.id, application_id)


@router.post(
    "/applications/{application_id}/mock-interviews",
    response_model=MockStartResponse,
    status_code=201,
)
def start_mock(
    application_id: str,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    """Start a mock interview: generate questions from the profile + job and return the first."""
    app = _get_app_or_404(conn, user.id, application_id)
    ctx = _context(user.id, app)
    job = catalogs_repo.get_job(conn, app["jobId"]) or {}
    profile = profiles_repo.get(conn, user.id)
    questions = ai_service.interview_questions(profile, job)

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
        "turns": [{"id": new_id("t"), "role": "coach", "text": questions[0], "timestamp": ts}],
        "transcript": "",
        "overallSummary": "",
        "dimensions": [],
        "improvementAdvice": "",
        "questions": questions,
        "currentIndex": 0,
        "status": "in_progress",
    }
    mocks_repo.create(conn, user.id, session)
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
    background_tasks: BackgroundTasks,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    """Submit a text answer; returns the next question, or the finished (scoring/complete) session."""
    _get_app_or_404(conn, user.id, application_id)
    session = _find_mock(conn, user.id, application_id, session_id)
    result = _process_turn(session, body.text, body.end, background_tasks)
    mocks_repo.save(conn, session)
    return result


@router.post(
    "/applications/{application_id}/mock-interviews/{session_id}/turns/voice",
    response_model=MockTurnResponse,
)
def submit_turn_voice(
    application_id: str,
    session_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    end: bool = Form(False),
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    """Submit a *spoken* answer for a mock interview turn.

    The uploaded audio is transcribed (STT) and then handled exactly like a text
    answer. Only available in real-AI mode.
    """
    if not ai_service.real_enabled():
        raise speech_not_supported()
    _get_app_or_404(conn, user.id, application_id)
    session = _find_mock(conn, user.id, application_id, session_id)

    name = (file.filename or "").lower()
    if not name.endswith(_ALLOWED_AUDIO_EXT):
        raise unsupported_audio_format()
    contents = file.file.read()
    if len(contents) > settings.audio_max_bytes:
        raise file_too_large("File is too large. Maximum size is 25 MB.")

    text = ai_service.transcribe(contents, file.filename or "answer")
    result = _process_turn(session, text, end, background_tasks)
    mocks_repo.save(conn, session)
    return result


@router.get("/applications/{application_id}/mock-interviews/{session_id}/turns/{turn_id}/audio")
def get_turn_audio(
    application_id: str,
    session_id: str,
    turn_id: str,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> Response:
    """Return the synthesized speech (TTS) for a coach turn.

    Audio is generated on demand and cached by turn id. Only available in
    real-AI mode.
    """
    if not ai_service.real_enabled():
        raise speech_not_supported()
    _get_app_or_404(conn, user.id, application_id)
    session = _find_mock(conn, user.id, application_id, session_id)
    turn = next((t for t in session["turns"] if t["id"] == turn_id), None)
    if not turn:
        raise not_found("Turn not found.")

    audio = tts_cache_repo.get(conn, turn_id)
    if audio is None:
        audio, _media = ai_service.synthesize(turn["text"])
        tts_cache_repo.put(conn, turn_id, audio)
    return Response(content=audio, media_type="audio/mpeg")


@router.get(
    "/applications/{application_id}/mock-interviews/{session_id}",
    response_model=MockInterviewSession,
)
def get_mock(
    application_id: str,
    session_id: str,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    """Return a mock interview session (used to poll for scoring completion)."""
    _get_app_or_404(conn, user.id, application_id)
    return _find_mock(conn, user.id, application_id, session_id)


@router.delete(
    "/applications/{application_id}/mock-interviews/{session_id}",
    status_code=204,
    response_model=None,
)
def delete_mock(
    application_id: str,
    session_id: str,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> None:
    """Delete a mock interview session; 404 if unknown."""
    if not mocks_repo.delete(conn, user.id, application_id, session_id):
        raise not_found("Mock session not found.")
