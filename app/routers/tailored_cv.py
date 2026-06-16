from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.errors import not_found, validation_error
from app.schemas.tailored_cv import TailoredCvRequest, TailoredCvResponse
from app.services import ai_service
from app.services.store import UserRecord, store

router = APIRouter(prefix="/tailored-cv", tags=["tailored-cv"])


@router.post("/generate", response_model=TailoredCvResponse)
def generate(body: TailoredCvRequest, user: UserRecord = Depends(get_current_user)) -> dict:
    '''
    Generate a tailored CV for a job.
    **Parameters**:
        - body: TailoredCvRequest: The request body.
        - user: UserRecord: The current user.
    **Returns**:
        - dict: The tailored CV.
    '''
    job = store.get_job(body.job_id)
    if not job:
        raise not_found("Job not found.")
    if body.goal_id not in store.goals.get(user.id, {}):
        raise validation_error("Goal not found.", "goalId")
    profile = store.profiles.get(user.id)
    return ai_service.generate_tailored_cv(profile, job)
