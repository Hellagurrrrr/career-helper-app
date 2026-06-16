"""Single entry point for every AI capability.

Routers depend only on this module. When ``settings.enable_real_ai`` is false
(default) every call falls back to the deterministic mock in
:mod:`app.services.mock_ai`; the ``app.llm.*`` packages (and their heavy
dependencies) are imported lazily so they are never required in mock mode.
"""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.services import mock_ai


def real_enabled() -> bool:
    return settings.enable_real_ai


# ---------------------------------------------------------------------------
# Mock-only helpers (fake progress animation + fixed onboarding script).
# Re-exported so routers never import mock_ai directly.
# ---------------------------------------------------------------------------
cv_extract_stage = mock_ai.cv_extract_stage
review_stage = mock_ai.review_stage
onboarding_total_questions = mock_ai.onboarding_total_questions
onboarding_field = mock_ai.onboarding_field
onboarding_question = mock_ai.onboarding_question
build_onboarding_draft = mock_ai.build_onboarding_draft
cv_extract_draft = mock_ai.cv_extract_draft
mock_review_analysis = mock_ai.mock_review_analysis
mock_interview_evaluation = mock_ai.mock_interview_evaluation


# ---------------------------------------------------------------------------
# Tailored CV (synchronous)
# ---------------------------------------------------------------------------
def generate_tailored_cv(profile: dict[str, Any] | None, job: dict[str, Any]) -> dict[str, Any]:
    if real_enabled():
        from app.llm.tailored_cv import generate_tailored_cv as _real

        return _real(profile, job)
    return mock_ai.generate_tailored_cv(profile, job)


# ---------------------------------------------------------------------------
# CV extraction (real path runs inside a background task)
# ---------------------------------------------------------------------------
def extract_profile_from_cv(cv_text: str) -> dict[str, Any]:
    from app.llm.cv_extraction import extract_profile_from_cv as _real

    return _real(cv_text)


# ---------------------------------------------------------------------------
# Interview coaching
# ---------------------------------------------------------------------------
def interview_questions(profile: dict[str, Any] | None, job: dict[str, Any]) -> list[str]:
    if real_enabled():
        from app.llm.interview import generate_questions

        return generate_questions(profile, job)
    return mock_ai.mock_interview_questions(job)


def analyze_transcript(transcript: str) -> dict[str, Any]:
    """Score a transcript -> {overallSummary, dimensions, improvementAdvice}."""
    from app.llm.interview import analyze_transcript as _real

    return _real(transcript)


# ---------------------------------------------------------------------------
# Conversational onboarding (real path uses LangGraph)
# ---------------------------------------------------------------------------
def onboarding_step(history: list[tuple[str, str]], target_questions: int) -> dict[str, Any]:
    from app.llm.onboarding import run_step

    return run_step(history, target_questions)


# ---------------------------------------------------------------------------
# Voice (STT / TTS)
# ---------------------------------------------------------------------------
def transcribe(audio_bytes: bytes, filename: str) -> str:
    from app.llm.voice import get_voice_provider

    return get_voice_provider().transcribe(audio_bytes, filename)


def synthesize(text: str) -> tuple[bytes, str]:
    from app.llm.voice import get_voice_provider

    return get_voice_provider().synthesize(text)
