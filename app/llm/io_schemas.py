"""Pydantic models used as LLM structured-output targets.

Field names are deliberately single words so ``model_dump()`` already matches
the camelCase JSON the frontend expects (camel == snake for one-word keys), and
the shapes mirror app/schemas/profile.py, tailored_cv.py and coaching.py.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# Fixed scoring dimensions (mirror app/services/mock_ai.py:_DIMENSIONS).
DIMENSION_IDS: list[tuple[str, str]] = [
    ("role_fit", "Role fit"),
    ("depth", "Technical depth"),
    ("communication", "Communication"),
    ("problem_solving", "Problem solving"),
    ("presence", "Presence"),
]


# --- Profile extraction (CV + conversational onboarding) ---
class EducationItem(BaseModel):
    degree: str = Field("", description="e.g. BSc, MSc, PhD")
    school: str = ""
    major: str = ""
    grade: float | None = Field(None, description="GPA on a 4.0 scale if known, else null")
    start: str = Field("", description="YYYY-MM if known, else empty")
    end: str | None = Field(None, description="YYYY-MM, or null if ongoing/unknown")


class InternshipItem(BaseModel):
    title: str = ""
    company: str = ""
    start: str = ""
    end: str | None = None
    description: str = ""


class ProjectItem(BaseModel):
    title: str = ""
    start: str = ""
    end: str | None = None
    description: str = ""


class ProfileDraft(BaseModel):
    """Partial profile the user confirms in the Review step."""

    name: str = ""
    education: list[EducationItem] = Field(default_factory=list)
    internships: list[InternshipItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    coursework: list[str] = Field(default_factory=list)


# --- Tailored CV ---
class TailoredCv(BaseModel):
    cv_text: str = Field(..., description="Full tailored CV as plain text")
    highlights: list[str] = Field(
        default_factory=list,
        description="2-4 short bullet points on why this candidate fits the role",
    )


# --- Interview coaching ---
class DimensionScore(BaseModel):
    id: str = Field(
        ..., description="One of: role_fit, depth, communication, problem_solving, presence"
    )
    label: str
    score: float = Field(..., description="0-10 scale, one decimal place")
    narrative: str = Field(..., description="One sentence of concrete feedback")


class InterviewAnalysis(BaseModel):
    overall_summary: str
    dimensions: list[DimensionScore] = Field(default_factory=list)
    improvement_advice: str


class InterviewQuestions(BaseModel):
    questions: list[str] = Field(..., description="Interview questions, most relevant first")


# --- Conversational onboarding step ---
class OnboardingStep(BaseModel):
    """One assistant turn: either ask the next question, or finish."""

    assessment: str = Field(
        "",
        description=(
            "Private note, never shown to the user: is the user's last answer clear, "
            "plausible and on-topic? What profile information is still missing or needs "
            "clarifying? Decide the next move based on this."
        ),
    )
    done: bool = Field(
        ...,
        description="True only when the core profile info is gathered or the user wants to stop",
    )
    question: str = Field(
        "",
        description=(
            "Your next chat message: briefly acknowledge the user's last answer, then ask "
            "ONE focused question or a gentle clarification. Empty when done=true."
        ),
    )
