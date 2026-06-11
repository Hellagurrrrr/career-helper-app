from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.common import CamelModel


class CoachingSummary(CamelModel):
    application_count: int
    review_count: int
    mock_count: int


class InterviewDimensionScore(CamelModel):
    id: str
    label: str
    score: float
    narrative: str


# ----- interview reviews -----
class InterviewReview(CamelModel):
    id: str
    application_id: str
    file_name: str
    uploaded_at: int
    duration_sec: int | None = None
    transcript: str
    overall_summary: str
    dimensions: list[InterviewDimensionScore] = Field(default_factory=list)
    improvement_advice: str


class ReviewCreatedResponse(CamelModel):
    id: str
    application_id: str
    status: str  # transcribing | summarizing | scoring | recommendations | complete


class ReviewStatusResponse(CamelModel):
    id: str
    application_id: str
    status: str
    review: InterviewReview | None = None


# ----- mock interviews -----
class MockInterviewTurn(CamelModel):
    id: str
    role: Literal["coach", "user"]
    text: str
    timestamp: int


class MockInterviewSession(CamelModel):
    id: str
    application_id: str
    job_title: str
    company: str
    goal_title: str | None = None
    skills: list[str] = Field(default_factory=list)
    started_at: int
    completed_at: int | None = None
    duration_sec: int | None = None
    turns: list[MockInterviewTurn] = Field(default_factory=list)
    transcript: str = ""
    overall_summary: str = ""
    dimensions: list[InterviewDimensionScore] = Field(default_factory=list)
    improvement_advice: str = ""


class MockStartResponse(CamelModel):
    session_id: str
    status: str
    question: str
    question_index: int
    total_questions: int


class MockTurnRequest(CamelModel):
    text: str = ""
    end: bool = False


class MockTurnResponse(CamelModel):
    status: str  # in_progress | complete
    question: str | None = None
    question_index: int | None = None
    total_questions: int | None = None
    session: MockInterviewSession | None = None
