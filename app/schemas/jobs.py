from __future__ import annotations

from pydantic import Field

from app.schemas.common import CamelModel


class JobListing(CamelModel):
    id: str
    catalog_goal_id: str
    title: str
    company: str
    company_tagline: str | None = None
    location: str
    type: str
    salary: str
    posted: str
    skills: list[str] = Field(default_factory=list)
    partner: bool
    exclusive: bool
    application_url: str | None = None
    description: str | None = None
    # Profile-vs-job match %, computed per request. Optional on the base model so
    # the list endpoint can include it; JobDetail makes it required.
    match_score: int | None = None


class JobDetail(JobListing):
    match_score: int


class JobListPage(CamelModel):
    items: list[JobListing]
    next_cursor: str | None = None
    total: int


class SaveJobRequest(CamelModel):
    goal_id: str
