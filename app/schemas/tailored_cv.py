from __future__ import annotations

from pydantic import Field

from app.schemas.common import CamelModel


class TailoredCvRequest(CamelModel):
    job_id: str
    goal_id: str


class TailoredCvResponse(CamelModel):
    cv_text: str
    highlights: list[str] = Field(default_factory=list)
