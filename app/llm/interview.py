"""Interview coaching: question generation and transcript scoring (real model)."""

from __future__ import annotations

import json
from typing import Any

from app.core.config import settings


def generate_questions(profile: dict[str, Any] | None, job: dict[str, Any]) -> list[str]:
    from app.llm.io_schemas import InterviewQuestions
    from app.llm.models import Purpose, get_llm
    from app.llm.prompts import INTERVIEW_QUESTIONS_SYSTEM

    profile_json = json.dumps(profile or {}, ensure_ascii=False)
    job_json = json.dumps(
        {"title": job.get("title"), "company": job.get("company"), "skills": job.get("skills", [])},
        ensure_ascii=False,
    )

    llm = get_llm(Purpose.INTERVIEW).with_structured_output(InterviewQuestions)
    result: InterviewQuestions = llm.invoke(
        [
            (
                "system",
                INTERVIEW_QUESTIONS_SYSTEM + f" Produce {settings.mock_question_count} questions.",
            ),
            ("human", f"Candidate profile:\n{profile_json}\n\nTarget job:\n{job_json}"),
        ]
    )
    questions = [q.strip() for q in result.questions if q.strip()]
    return questions[: settings.mock_question_count] or ["Tell me about yourself."]


def analyze_transcript(transcript: str) -> dict[str, Any]:
    """Score an interview transcript on the five fixed dimensions.

    Returns ``overallSummary`` / ``dimensions`` / ``improvementAdvice`` (the
    caller owns ``transcript`` and ``durationSec``).
    """
    from app.llm.io_schemas import InterviewAnalysis
    from app.llm.models import Purpose, get_llm
    from app.llm.prompts import INTERVIEW_SCORING_SYSTEM

    llm = get_llm(Purpose.INTERVIEW).with_structured_output(InterviewAnalysis)
    analysis: InterviewAnalysis = llm.invoke(
        [
            ("system", INTERVIEW_SCORING_SYSTEM),
            ("human", f"Interview transcript:\n\n{transcript}"),
        ]
    )
    return {
        "overallSummary": analysis.overall_summary,
        "dimensions": [d.model_dump() for d in analysis.dimensions],
        "improvementAdvice": analysis.improvement_advice,
    }
