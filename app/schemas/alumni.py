from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.common import CamelModel


class AlumniProfile(CamelModel):
    id: str
    first_name: str
    last_initial: str
    role: str
    company: str
    industry: str
    graduation_year: int
    major: str
    university: str
    years_experience: int
    bio: str
    expertise: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    response_time: str
    availability: str
    goal_alignment: list[str] = Field(default_factory=list)
    avatar_gradient: str
    linkedin_url: str


class MeetingRequest(CamelModel):
    id: str
    alumni_id: str
    topic: str
    message: str
    preferred_times: list[str] = Field(default_factory=list)
    submitted_at: int
    status: Literal["pending", "completed", "withdrawn"]
    completed_at: int | None = None


class CreateMeetingRequest(CamelModel):
    alumni_id: str
    topic: str
    message: str
    preferred_times: list[str] = Field(default_factory=list)


class UpdateMeetingRequest(CamelModel):
    status: Literal["completed", "withdrawn"]
