from __future__ import annotations

from typing import Literal

from app.schemas.common import CamelModel

ManualApplicationStatus = Literal[
    "applied", "screening", "interview", "offer", "rejected", "withdrawn"
]
PartnerPipelineCode = Literal[
    "referral_sent", "under_review", "interview", "final_round", "offer_extended"
]


class JobApplication(CamelModel):
    id: str
    kind: Literal["partner", "standard"]
    goal_id: str
    job_id: str
    title: str
    company: str
    submitted_at: int
    partner_status: PartnerPipelineCode | None = None
    manual_status: ManualApplicationStatus | None = None
    review_count: int = 0
    mock_count: int = 0


class ApplicationSummary(CamelModel):
    total: int
    partner: int
    self_tracked: int
    in_progress: int
    offers: int


class ApplicationListResponse(CamelModel):
    items: list[JobApplication]
    summary: ApplicationSummary


class CreateApplicationRequest(CamelModel):
    kind: Literal["partner", "standard"]
    goal_id: str
    job_id: str
    cv_text: str | None = None


class UpdateApplicationRequest(CamelModel):
    manual_status: ManualApplicationStatus
