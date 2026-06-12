from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.errors import APIError, file_too_large, not_found, validation_error
from app.core.security import new_id, now_ms
from app.services import mock_ai, notifications_service
from app.schemas.profile import (
    CvExtractResult,
    CvExtractTask,
    OnboardingAnswerRequest,
    OnboardingChatSession,
    Profile,
    ProfileInput,
)
from app.services.store import UserRecord, store

router = APIRouter(prefix="/profile", tags=["profile"])

_ALLOWED_CV_EXT = (".pdf", ".doc", ".docx", ".txt")


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
def get_profile(user: UserRecord = Depends(get_current_user)) -> Profile:
    '''
    Get the profile of the current user.

    **Args**:
        -  user: UserRecord: The current user.
    **Returns**:
        - Profile: The profile of the current user.
    **Raises**:
        - not_found: If the profile has not been created yet.
    '''
    data = store.profiles.get(user.id)
    if not data:
        raise not_found("Profile has not been created yet.")
    return Profile.model_validate(data)


@router.put("", response_model=Profile)
def put_profile(body: ProfileInput, user: UserRecord = Depends(get_current_user)) -> Profile:
    '''
    Put the profile of the current user.

    **Args**:
        - body: ProfileInput: The profile input.
        - user: UserRecord: The current user.
    **Returns**:
        - Profile: The profile of the current user.
    '''
    was_empty = not store.profiles.get(user.id)
    record = _normalize_profile(body.model_dump(by_alias=True))
    record["updatedAt"] = now_ms()
    store.profiles[user.id] = record
    # First-time creation = onboarding completion -> welcome notification (OB-03/04/13).
    if was_empty:
        notifications_service.welcome(user.id, record.get("name", ""))
    return Profile.model_validate(record)


@router.post("/extract-cv", response_model=CvExtractTask, status_code=status.HTTP_202_ACCEPTED)
def extract_cv(
    file: UploadFile = File(...),
    user: UserRecord = Depends(get_current_user),
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
    store.cv_tasks[task_id] = {
        "userId": user.id,
        "fileName": file.filename or "cv",
        "polls": 0,
    }
    return CvExtractTask(task_id=task_id, status="processing")


@router.get("/extract-cv/{task_id}", response_model=CvExtractResult)
def get_extract_cv(task_id: str, user: UserRecord = Depends(get_current_user)) -> CvExtractResult:
    '''
    Get the result of the CV extraction task.

    **Args**:
        - task_id: str: The ID of the CV extraction task.
        - user: UserRecord: The current user.
    **Returns**:
        - CvExtractResult: The result of the CV extraction task.
    '''
    task = store.cv_tasks.get(task_id)
    if not task or task["userId"] != user.id:
        raise not_found("Extraction task not found.")

    task["polls"] += 1
    polls = task["polls"]
    if polls <= settings.async_processing_polls:
        return CvExtractResult(
            task_id=task_id,
            status="processing",
            stage=mock_ai.cv_extract_stage(polls),
        )
    return CvExtractResult(
        task_id=task_id,
        status="complete",
        stage="structuring",
        draft=mock_ai.cv_extract_draft(task["fileName"]),
    )


# ---------------------------------------------------------------------------
# Conversational onboarding collection (api-design 3.4 / use-case OB-10~12)
# ---------------------------------------------------------------------------
def _new_chat_session() -> dict[str, Any]:
    ts = now_ms()
    first_question = mock_ai.onboarding_question(0)
    return {
        "id": new_id("obc"),
        "status": "in_progress",
        "question": first_question,
        "questionIndex": 0,
        "totalQuestions": mock_ai.onboarding_total_questions(),
        "turns": [
            {"id": new_id("t"), "role": "assistant", "text": first_question, "timestamp": ts}
        ],
        "answers": {},
        "draft": None,
    }


@router.post("/onboarding-chat", response_model=OnboardingChatSession)
def start_onboarding_chat(user: UserRecord = Depends(get_current_user)) -> dict:
    '''
    Start or resume the conversational onboarding session.

    If an in-progress session already exists it is returned as-is so the user
    continues from where they left off (use-case OB-12); otherwise a new session
    is created with the first assistant question.
    '''
    existing = store.onboarding_chats.get(user.id)
    if existing and existing.get("status") == "in_progress":
        return existing
    session = _new_chat_session()
    store.onboarding_chats[user.id] = session
    return session


@router.get("/onboarding-chat", response_model=OnboardingChatSession)
def get_onboarding_chat(user: UserRecord = Depends(get_current_user)) -> dict:
    '''Get the current onboarding chat session; 404 if none exists.'''
    session = store.onboarding_chats.get(user.id)
    if not session:
        raise not_found("No onboarding chat session.")
    return session


@router.post("/onboarding-chat/answers", response_model=OnboardingChatSession)
def answer_onboarding_chat(
    body: OnboardingAnswerRequest,
    user: UserRecord = Depends(get_current_user),
) -> dict:
    '''
    Submit an answer to the current question. The assistant records it and either
    asks the next question or, once enough info is collected, completes the
    session and returns a profile `draft` for the Review step (use-case OB-10).
    '''
    session = store.onboarding_chats.get(user.id)
    if not session:
        raise not_found("No onboarding chat session.")
    if session["status"] == "complete":
        raise APIError("VALIDATION_ERROR", 422, "Onboarding chat is already complete.")

    text = body.text.strip()
    if not text:
        raise validation_error("Please enter a message.", "text")

    index = session["questionIndex"]
    field = mock_ai.onboarding_field(index)
    session["answers"][field] = text
    session["turns"].append(
        {"id": new_id("t"), "role": "user", "text": text, "timestamp": now_ms()}
    )

    next_index = index + 1
    next_question = mock_ai.onboarding_question(next_index)
    session["questionIndex"] = next_index

    if next_question is not None:
        session["question"] = next_question
        session["turns"].append(
            {"id": new_id("t"), "role": "assistant", "text": next_question, "timestamp": now_ms()}
        )
    else:
        # Assistant has enough info -> finish and produce the draft.
        session["status"] = "complete"
        session["question"] = None
        session["draft"] = mock_ai.build_onboarding_draft(session["answers"])

    return session


@router.delete("/onboarding-chat", status_code=204, response_model=None)
def delete_onboarding_chat(user: UserRecord = Depends(get_current_user)) -> None:
    '''Discard the current onboarding chat session (restart / leave chat mode).'''
    if not store.onboarding_chats.get(user.id):
        raise not_found("No onboarding chat session.")
    store.onboarding_chats[user.id] = None
