from __future__ import annotations

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


def _run_review_analysis(review: dict[str, Any], audio_bytes: bytes, filename: str) -> None:
    """Real-AI background job: transcribe the recording, then score the transcript."""
    try:
        review["status"] = "transcribing"
        transcript = ai_service.transcribe(audio_bytes, filename)
        review["transcript"] = transcript
        review["status"] = "scoring"
        analysis = ai_service.analyze_transcript(transcript)
        review["overallSummary"] = analysis["overallSummary"]
        review["dimensions"] = analysis["dimensions"]
        review["improvementAdvice"] = analysis["improvementAdvice"]
        review["status"] = "complete"
    except Exception as exc:  # noqa: BLE001 - surface failure to the poller
        review["status"] = "failed"
        review["error"] = str(exc)


# ---------------------------------------------------------------------------
# Page-level (api-design 9.1)
# ---------------------------------------------------------------------------
@router.get("/ai-coaching/summary", response_model=CoachingSummary)
def coaching_summary(user: UserRecord = Depends(get_current_user)) -> dict:
    '''
    Get the coaching summary.
    **Parameters**:
        - user: UserRecord: The current user.
    **Returns**:
        - dict: The coaching summary.
    '''
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
    '''
    Get the coaching applications.
    **Parameters**:
        - user: UserRecord: The current user.
    **Returns**:
        - list[dict]: The list of coaching applications.
    '''
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
    '''
    List the interview reviews for an application.
    **Parameters**:
        - application_id: str: The ID of the application.
        - user: UserRecord: The current user.
    **Returns**:
        - list[dict]: The list of interview reviews.
    '''
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
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: UserRecord = Depends(get_current_user),
) -> dict:
    '''
    Create an interview review for an application.
    **Parameters**:
        - application_id: str: The ID of the application.
        - file: UploadFile: The audio file to upload.
        - user: UserRecord: The current user.
    **Returns**:
        - dict: The interview review.
    '''
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
) -> dict:
    '''
    Get the status of an interview review.
    **Parameters**:
        - application_id: str: The ID of the application.
        - review_id: str: The ID of the review.
        - user: UserRecord: The current user.
    **Returns**:
        - dict: The status of the interview review.
    '''
    _get_app_or_404(user.id, application_id)
    reviews = store.reviews.get(user.id, {}).get(application_id, [])
    review = next((r for r in reviews if r["id"] == review_id), None)
    if not review:
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
                return {"id": review_id, "applicationId": application_id, "status": review["status"]}
            analysis = ai_service.mock_review_analysis(review["fileName"])
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
    '''
    Delete an interview review for an application.
    **Parameters**:
        - application_id: str: The ID of the application.
        - review_id: str: The ID of the review.
        - user: UserRecord: The current user.
    **Returns**:
        - None: The response body.
    '''
    reviews = store.reviews.get(user.id, {}).get(application_id, [])
    idx = next((i for i, r in enumerate(reviews) if r["id"] == review_id), None)
    if idx is None:
        raise not_found("Review not found.")
    reviews.pop(idx)


# ---------------------------------------------------------------------------
# Mock interviews (api-design 9.6)
# ---------------------------------------------------------------------------
def _build_transcript(turns: list[dict[str, Any]]) -> str:
    return "\n".join(f"{t['role']}: {t['text']}" for t in turns)


def _run_mock_scoring(session: dict[str, Any]) -> None:
    """Real-AI background job: score a finished mock interview transcript."""
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


def _finalize_response(session: dict[str, Any], background_tasks: BackgroundTasks) -> dict[str, Any]:
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


def _find_mock(user_id: str, application_id: str, session_id: str) -> dict[str, Any]:
    sessions = store.mocks.get(user_id, {}).get(application_id, [])
    session = next((s for s in sessions if s["id"] == session_id), None)
    if not session:
        raise not_found("Mock session not found.")
    return session


@router.get(
    "/applications/{application_id}/mock-interviews",
    response_model=list[MockInterviewSession],
)
def list_mocks(application_id: str, user: UserRecord = Depends(get_current_user)) -> list[dict]:
    '''
    List the mock interviews for an application.
    **Parameters**:
        - application_id: str: The ID of the application.
        - user: UserRecord: The current user.
    **Returns**:
        - list[dict]: The list of mock interviews.
    '''
    _get_app_or_404(user.id, application_id)
    sessions = store.mocks.get(user.id, {}).get(application_id, [])
    return sorted(sessions, key=lambda s: s["startedAt"], reverse=True)


@router.post(
    "/applications/{application_id}/mock-interviews",
    response_model=MockStartResponse,
    status_code=201,
)
def start_mock(application_id: str, user: UserRecord = Depends(get_current_user)) -> dict:
    '''
    Start a mock interview for an application.
    **Parameters**:
        - application_id: str: The ID of the application.
        - user: UserRecord: The current user.
    **Returns**:
        - dict: The mock interview.
    '''
    app = _get_app_or_404(user.id, application_id)
    ctx = _context(user.id, app)
    job = store.get_job(app["jobId"]) or {}
    profile = store.profiles.get(user.id)
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
    background_tasks: BackgroundTasks,
    user: UserRecord = Depends(get_current_user),
) -> dict:
    '''
    Submit a text answer for a mock interview turn.
    **Parameters**:
        - application_id: str: The ID of the application.
        - session_id: str: The ID of the session.
        - body: MockTurnRequest: The request body (text answer or end flag).
        - user: UserRecord: The current user.
    **Returns**:
        - dict: The next question, or the (scoring/complete) session.
    '''
    _get_app_or_404(user.id, application_id)
    session = _find_mock(user.id, application_id, session_id)
    return _process_turn(session, body.text, body.end, background_tasks)


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
) -> dict:
    '''
    Submit a *spoken* answer for a mock interview turn.

    The uploaded audio is transcribed (STT) and then handled exactly like a text
    answer. Only available in real-AI mode.
    '''
    if not ai_service.real_enabled():
        raise speech_not_supported()
    _get_app_or_404(user.id, application_id)
    session = _find_mock(user.id, application_id, session_id)

    name = (file.filename or "").lower()
    if not name.endswith(_ALLOWED_AUDIO_EXT):
        raise unsupported_audio_format()
    contents = file.file.read()
    if len(contents) > settings.audio_max_bytes:
        raise file_too_large("File is too large. Maximum size is 25 MB.")

    text = ai_service.transcribe(contents, file.filename or "answer")
    return _process_turn(session, text, end, background_tasks)


@router.get("/applications/{application_id}/mock-interviews/{session_id}/turns/{turn_id}/audio")
def get_turn_audio(
    application_id: str,
    session_id: str,
    turn_id: str,
    user: UserRecord = Depends(get_current_user),
) -> Response:
    '''
    Return the synthesized speech (TTS) for a coach turn. Audio is generated on
    demand and cached by turn id. Only available in real-AI mode.
    '''
    if not ai_service.real_enabled():
        raise speech_not_supported()
    _get_app_or_404(user.id, application_id)
    session = _find_mock(user.id, application_id, session_id)
    turn = next((t for t in session["turns"] if t["id"] == turn_id), None)
    if not turn:
        raise not_found("Turn not found.")

    audio = store.tts_cache.get(turn_id)
    if audio is None:
        audio, _media = ai_service.synthesize(turn["text"])
        store.tts_cache[turn_id] = audio
    return Response(content=audio, media_type="audio/mpeg")


@router.get(
    "/applications/{application_id}/mock-interviews/{session_id}",
    response_model=MockInterviewSession,
)
def get_mock(
    application_id: str,
    session_id: str,
    user: UserRecord = Depends(get_current_user),
) -> dict:
    '''
    Get a mock interview for an application.
    **Parameters**:
        - application_id: str: The ID of the application.
        - session_id: str: The ID of the session.
        - user: UserRecord: The current user.
    **Returns**:
        - dict: The mock interview.
    '''
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
    '''
    Delete a mock interview for an application.
    **Parameters**:
        - application_id: str: The ID of the application.
        - session_id: str: The ID of the session.
        - user: UserRecord: The current user.
    **Returns**:
        - None: The response body.
    '''
    sessions = store.mocks.get(user.id, {}).get(application_id, [])
    idx = next((i for i, s in enumerate(sessions) if s["id"] == session_id), None)
    if idx is None:
        raise not_found("Mock session not found.")
    sessions.pop(idx)
