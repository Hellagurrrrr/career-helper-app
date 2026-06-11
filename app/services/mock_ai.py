from __future__ import annotations

from typing import Any

from app.core.config import settings

# ---------------------------------------------------------------------------
# CV extraction (api-design 3.3 / use-case OB-09)
# ---------------------------------------------------------------------------

_CV_STAGES = ["parsing", "extracting", "structuring"]


def cv_extract_stage(polls: int) -> str:
    """Map a poll count to a 3-stage progress label for the frontend animation."""
    idx = min(polls - 1, len(_CV_STAGES) - 1)
    return _CV_STAGES[max(idx, 0)]


def cv_extract_draft(file_name: str) -> dict[str, Any]:
    """Return a mock extracted profile draft.

    Mirrors the demo result described in api-design 3.3: a partial Profile the
    user confirms in the Review step before PUT /profile.
    """
    return {
        "name": "Alex Chen",
        "skills": ["Python", "SQL", "React"],
        "coursework": ["Data Structures", "Databases"],
        "education": [
            {
                "degree": "BSc",
                "school": "State University",
                "major": "Computer Science",
                "grade": 3.7,
                "start": "2022-09",
                "end": "2026-06",
            }
        ],
        "projects": [
            {
                "title": "Project extracted from CV",
                "start": "2025-09",
                "end": "2025-12",
                "description": f"Auto-extracted from {file_name}.",
            }
        ],
        "internships": [],
    }


# ---------------------------------------------------------------------------
# Tailored CV (api-design 7)
# ---------------------------------------------------------------------------


def generate_tailored_cv(profile: dict[str, Any] | None, job: dict[str, Any]) -> dict[str, Any]:
    name = (profile or {}).get("name") or "Your Name"
    profile_skills = set((profile or {}).get("skills", []))
    job_skills = list(job.get("skills", []))
    matched = [s for s in job_skills if s in profile_skills]

    lines = [
        name.upper(),
        f"Candidate for {job.get('title', 'the role')} at {job.get('company', 'the company')}",
        "",
        "SUMMARY",
        f"Motivated candidate aligned with {job.get('title', 'this role')}. "
        f"Strengths in {', '.join(sorted(profile_skills)) or 'relevant skills'}.",
        "",
        "SKILLS",
        ", ".join(sorted(profile_skills)) or "—",
    ]
    cv_text = "\n".join(lines)

    highlights = [
        f"Matched {len(matched)}/{len(job_skills)} required skills"
        if job_skills
        else "Tailored to the role",
    ]
    if matched:
        highlights.append(f"Emphasized {matched[0]} experience")
    return {"cvText": cv_text, "highlights": highlights}


# ---------------------------------------------------------------------------
# Interview coaching: dimension scores (api-design 9.2)
# ---------------------------------------------------------------------------

_DIMENSIONS = [
    ("role_fit", "Role fit"),
    ("depth", "Technical depth"),
    ("communication", "Communication"),
    ("problem_solving", "Problem solving"),
    ("presence", "Presence"),
]


def mock_dimensions(seed: int = 0) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, (dim_id, label) in enumerate(_DIMENSIONS):
        score = round(6.5 + ((seed + i) % 4) * 0.6, 1)  # 6.5 - 8.3, demo 1-10 scale
        out.append(
            {
                "id": dim_id,
                "label": label,
                "score": score,
                "narrative": f"Solid {label.lower()}; keep refining with concrete examples.",
            }
        )
    return out


def mock_review_analysis(file_name: str) -> dict[str, Any]:
    return {
        "transcript": f"[Mock transcript generated from {file_name}.]",
        "overallSummary": "A confident interview with clear structure; tighten quantified impact.",
        "dimensions": mock_dimensions(seed=len(file_name)),
        "improvementAdvice": "Lead with results, then explain the approach. Practice concise STAR answers.",
    }


def review_stage(polls: int) -> str:
    """Map poll count to interview-review analysis step (api-design 9.3)."""
    steps = ["transcribing", "summarizing", "scoring", "recommendations"]
    idx = min(polls - 1, len(steps) - 1)
    return steps[max(idx, 0)]


# ---------------------------------------------------------------------------
# Mock interview questions & evaluation (api-design 9.6)
# ---------------------------------------------------------------------------


def mock_interview_questions(job: dict[str, Any]) -> list[str]:
    title = job.get("title", "this role")
    skills = job.get("skills", [])
    questions = [
        f"Tell me about your interest in the {title} position.",
        f"Describe a project where you used {skills[0] if skills else 'a key skill'}.",
        "Walk me through how you approach an unfamiliar problem.",
        "Tell me about a time you collaborated to ship something under a deadline.",
    ]
    return questions[: settings.mock_question_count]


def mock_interview_evaluation(turns: list[dict[str, Any]]) -> dict[str, Any]:
    user_answers = [t for t in turns if t.get("role") == "user"]
    transcript = "\n".join(f"{t['role']}: {t['text']}" for t in turns)
    return {
        "transcript": transcript,
        "overallSummary": f"Answered {len(user_answers)} question(s) with steady delivery.",
        "dimensions": mock_dimensions(seed=len(user_answers)),
        "improvementAdvice": "Add specific metrics and structure answers with situation-action-result.",
    }
