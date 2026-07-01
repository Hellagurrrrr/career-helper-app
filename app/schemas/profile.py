from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.common import CamelModel


class Education(CamelModel):
    degree: str = ""
    school: str = ""
    major: str = ""
    grade: float | None = None
    start: str = ""
    end: str | None = None


class Internship(CamelModel):
    title: str = ""
    company: str = ""
    start: str = ""
    end: str | None = None
    description: str = ""


class Project(CamelModel):
    title: str = ""
    start: str = ""
    end: str | None = None
    description: str = ""


class ProfileInput(CamelModel):
    name: str = ""
    education: list[Education] = Field(default_factory=list)
    internships: list[Internship] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    coursework: list[str] = Field(default_factory=list)


class Profile(ProfileInput):
    updated_at: int


class CvExtractTask(CamelModel):
    task_id: str
    status: str  # processing | complete | failed


class CvExtractResult(CamelModel):
    task_id: str
    status: str  # processing | complete | failed
    stage: str  # parsing | extracting | structuring
    draft: dict | None = None


class OnboardingChatTurn(CamelModel):
    id: str
    role: Literal["assistant", "user"]
    text: str
    timestamp: int


class OnboardingChatSession(CamelModel):
    id: str
    status: Literal["in_progress", "complete"]
    question: str | None = None
    question_index: int
    total_questions: int
    turns: list[OnboardingChatTurn] = Field(default_factory=list)
    draft: dict | None = None


class OnboardingAnswerRequest(CamelModel):
    text: str = ""
