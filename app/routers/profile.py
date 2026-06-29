from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.errors import APIError, file_too_large, not_found, validation_error
from app.core.security import new_id, now_ms
from app.db import get_conn, get_connection
from app.repositories import cv_tasks as cv_tasks_repo
from app.repositories import onboarding_chats as onboarding_chats_repo
from app.repositories import profiles as profiles_repo
from app.services import ai_service, notifications_service
from app.schemas.profile import (
    CvExtractResult,
    CvExtractTask,
    OnboardingAnswerRequest,
    OnboardingChatSession,
    Profile,
    ProfileInput,
)
from app.services.store import UserRecord

router = APIRouter(prefix="/profile", tags=["profile"])

_ALLOWED_CV_EXT = (".pdf", ".doc", ".docx", ".txt")


def _run_cv_extraction(task_id: str, filename: str, contents: bytes) -> None:
    """Real-AI background job: parse the file, then extract a profile draft.

    Progress is reported through the task's ``stage`` field so the frontend
    polling animation still has parsing -> extracting -> structuring to show.
    """
    # Runs in a BackgroundTask thread (no request scope), so it pulls the shared
    # connection directly and commits after each step the poller may observe.
    conn = get_connection()
    if cv_tasks_repo.get(conn, task_id) is None:
        return
    try:
        from app.llm.parsing import extract_text

        cv_tasks_repo.set_stage(conn, task_id, "parsing")
        conn.commit()
        text = extract_text(filename, contents)
        cv_tasks_repo.set_stage(conn, task_id, "extracting")
        conn.commit()
        draft = ai_service.extract_profile_from_cv(text)
        cv_tasks_repo.complete(conn, task_id, draft)
        conn.commit()
    except Exception as exc:  # noqa: BLE001 - surface any failure to the poller
        cv_tasks_repo.fail(conn, task_id, str(exc))
        conn.commit()


def _normalize_profile(record: dict[str, Any]) -> dict[str, Any]:
    """Apply Review-step normalization (use-case OB-13).

    - Empty-string `end` -> null for dated entries (in progress / present).
    - Drop fully-empty internship entries.
    """
    for edu in record.get("education", []):
        if edu.get("end") == "":
            edu["end"] = None
    for proj in record.get("projects", []):
        if proj.get("end") == "":
            proj["end"] = None
    kept_internships = []
    for intern in record.get("internships", []):
        if intern.get("end") == "":
            intern["end"] = None
        if any(intern.get(k) for k in ("title", "company", "description", "start")):
            kept_internships.append(intern)
    record["internships"] = kept_internships
    return record


@router.get("", response_model=Profile)
def get_profile(
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> Profile:
    '''
    Get the profile of the current user.

    **Args**:
        -  user: UserRecord: The current user.
    **Returns**:
        - Profile: The profile of the current user.
    **Raises**:
        - not_found: If the profile has not been created yet.
    '''
    data = profiles_repo.get(conn, user.id)
    if not data:
        raise not_found("Profile has not been created yet.")
    return Profile.model_validate(data)


@router.put("", response_model=Profile)
def put_profile(
    body: ProfileInput,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> Profile:
    '''
    Put the profile of the current user.

    **Args**:
        - body: ProfileInput: The profile input.
        - user: UserRecord: The current user.
    **Returns**:
        - Profile: The profile of the current user.
    '''
    was_empty = not profiles_repo.get(conn, user.id)
    record = _normalize_profile(body.model_dump(by_alias=True))
    record["updatedAt"] = now_ms()
    profiles_repo.save(conn, user.id, record)
    # First-time creation = onboarding completion -> welcome notification (OB-03/04/13).
    if was_empty:
        notifications_service.welcome(user.id, record.get("name", ""))
    return Profile.model_validate(record)


@router.post("/extract-cv", response_model=CvExtractTask, status_code=status.HTTP_202_ACCEPTED)
def extract_cv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> CvExtractTask:
    '''
    Extract the CV of the current user:
    - Upload a CV file and start the extraction process.
    - The extraction process is asynchronous and the result will be returned via a polling endpoint.

    **Args**:
        - file: UploadFile: The CV file.
        - user: UserRecord: The current user.
    **Returns**:
        - CvExtractTask: The task of the CV extraction.
    '''
    name = (file.filename or "").lower()
    if not name.endswith(_ALLOWED_CV_EXT):
        raise validation_error("Unsupported file type. Use PDF, DOC, DOCX, or TXT.", "file")

    contents = file.file.read()
    if len(contents) > settings.cv_max_bytes:
        raise file_too_large("File is too large. Maximum size is 10 MB.")

    task_id = new_id("task")
    cv_tasks_repo.create(conn, task_id=task_id, user_id=user.id, file_name=file.filename or "cv")
    if ai_service.real_enabled():
        # Real AI: parse + call the model in a background task; GET reads status.
        background_tasks.add_task(_run_cv_extraction, task_id, file.filename or "cv", contents)
    # Mock mode just advances a poll counter on each GET (see get_extract_cv).
    return CvExtractTask(task_id=task_id, status="processing")


@router.get("/extract-cv/{task_id}", response_model=CvExtractResult)
def get_extract_cv(
    task_id: str,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> CvExtractResult:
    '''
    Get the result of the CV extraction task.

    **Args**:
        - task_id: str: The ID of the CV extraction task.
        - user: UserRecord: The current user.
    **Returns**:
        - CvExtractResult: The result of the CV extraction task.
    '''
    task = cv_tasks_repo.get(conn, task_id)
    if not task or task["user_id"] != user.id:
        raise not_found("Extraction task not found.")

    if ai_service.real_enabled():
        # Real AI: just report whatever the background task has written so far.
        return CvExtractResult(
            task_id=task_id,
            status=task["status"] or "processing",
            stage=task["stage"] or "extracting",
            draft=task["draft"],
        )

    # Mock: simulate progress via the poll counter.
    polls = cv_tasks_repo.increment_polls(conn, task_id)
    if polls <= settings.async_processing_polls:
        return CvExtractResult(
            task_id=task_id,
            status="processing",
            stage=ai_service.cv_extract_stage(polls),
        )
    return CvExtractResult(
        task_id=task_id,
        status="complete",
        stage="structuring",
        draft=ai_service.cv_extract_draft(task["file_name"]),
    )


# ---------------------------------------------------------------------------
# Conversational onboarding collection (api-design 3.4 / use-case OB-10~12)
# ---------------------------------------------------------------------------
_DEFAULT_FIRST_QUESTION = "Hi! I'm your career assistant. What's your name?"


def _new_chat_session() -> dict[str, Any]:
    ts = now_ms()
    if ai_service.real_enabled():
        step = ai_service.onboarding_step([], settings.onboarding_target_questions)
        first_question = step.get("question") or _DEFAULT_FIRST_QUESTION
        total = settings.onboarding_target_questions
    else:
        first_question = ai_service.onboarding_question(0)
        total = ai_service.onboarding_total_questions()
    return {
        "id": new_id("obc"),
        "status": "in_progress",
        "question": first_question,
        "questionIndex": 0,
        "totalQuestions": total,
        "turns": [
            {"id": new_id("t"), "role": "assistant", "text": first_question, "timestamp": ts}
        ],
        "answers": {},
        "draft": None,
    }


def _advance_mock_onboarding(session: dict[str, Any], text: str) -> None:
    """Fixed-script flow: map the answer to a field and ask the next question."""
    index = session["questionIndex"]
    field = ai_service.onboarding_field(index)
    session["answers"][field] = text

    next_index = index + 1
    next_question = ai_service.onboarding_question(next_index)
    session["questionIndex"] = next_index

    if next_question is not None:
        session["question"] = next_question
        session["turns"].append(
            {"id": new_id("t"), "role": "assistant", "text": next_question, "timestamp": now_ms()}
        )
    else:
        session["status"] = "complete"
        session["question"] = None
        session["draft"] = ai_service.build_onboarding_draft(session["answers"])


def _advance_real_onboarding(session: dict[str, Any]) -> None:
    """LangGraph flow: replay the conversation, then ask next or finish + draft."""
    history = [
        ("ai" if turn["role"] == "assistant" else "human", turn["text"])
        for turn in session["turns"]
    ]
    result = ai_service.onboarding_step(history, session["totalQuestions"])
    if result.get("done"):
        session["status"] = "complete"
        session["question"] = None
        session["draft"] = result.get("draft")
    else:
        question = result.get("question") or "Could you tell me a bit more about yourself?"
        session["questionIndex"] += 1
        session["question"] = question
        session["turns"].append(
            {"id": new_id("t"), "role": "assistant", "text": question, "timestamp": now_ms()}
        )


@router.post("/onboarding-chat", response_model=OnboardingChatSession)
def start_onboarding_chat(
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    '''
    Start or resume the conversational onboarding session.

    If an in-progress session already exists it is returned as-is so the user
    continues from where they left off (use-case OB-12); otherwise a new session
    is created with the first assistant question.
    '''
    existing = onboarding_chats_repo.get(conn, user.id)
    if existing and existing.get("status") == "in_progress":
        return existing
    session = _new_chat_session()
    onboarding_chats_repo.save(conn, user.id, session)
    return session


@router.get("/onboarding-chat", response_model=OnboardingChatSession)
def get_onboarding_chat(
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    '''Get the current onboarding chat session; 404 if none exists.'''
    session = onboarding_chats_repo.get(conn, user.id)
    if not session:
        raise not_found("No onboarding chat session.")
    return session


@router.post("/onboarding-chat/answers", response_model=OnboardingChatSession)
def answer_onboarding_chat(
    body: OnboardingAnswerRequest,
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    '''
    Submit an answer to the current question. The assistant records it and either
    asks the next question or, once enough info is collected, completes the
    session and returns a profile `draft` for the Review step (use-case OB-10).
    '''
    session = onboarding_chats_repo.get(conn, user.id)
    if not session:
        raise not_found("No onboarding chat session.")
    if session["status"] == "complete":
        raise APIError("VALIDATION_ERROR", 422, "Onboarding chat is already complete.")

    text = body.text.strip()
    if not text:
        raise validation_error("Please enter a message.", "text")

    session["turns"].append(
        {"id": new_id("t"), "role": "user", "text": text, "timestamp": now_ms()}
    )

    if ai_service.real_enabled():
        _advance_real_onboarding(session)
    else:
        _advance_mock_onboarding(session, text)

    onboarding_chats_repo.save(conn, user.id, session)
    return session


@router.delete("/onboarding-chat", status_code=204, response_model=None)
def delete_onboarding_chat(
    user: UserRecord = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> None:
    '''Discard the current onboarding chat session (restart / leave chat mode).'''
    if not onboarding_chats_repo.delete(conn, user.id):
        raise not_found("No onboarding chat session.")
