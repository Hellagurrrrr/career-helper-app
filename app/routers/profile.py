from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.errors import file_too_large, not_found, validation_error
from app.core.security import new_id, now_ms
from app.services import mock_ai
from app.schemas.profile import CvExtractResult, CvExtractTask, Profile, ProfileInput
from app.services.store import UserRecord, store

router = APIRouter(prefix="/profile", tags=["profile"])

_ALLOWED_CV_EXT = (".pdf", ".doc", ".docx", ".txt")


@router.get("", response_model=Profile)
def get_profile(user: UserRecord = Depends(get_current_user)) -> Profile:
    data = store.profiles.get(user.id)
    if not data:
        raise not_found("Profile has not been created yet.")
    return Profile.model_validate(data)


@router.put("", response_model=Profile)
def put_profile(body: ProfileInput, user: UserRecord = Depends(get_current_user)) -> Profile:
    record = body.model_dump(by_alias=True)
    record["updatedAt"] = now_ms()
    store.profiles[user.id] = record
    return Profile.model_validate(record)


@router.post("/extract-cv", response_model=CvExtractTask, status_code=status.HTTP_202_ACCEPTED)
def extract_cv(
    file: UploadFile = File(...),
    user: UserRecord = Depends(get_current_user),
) -> CvExtractTask:
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
