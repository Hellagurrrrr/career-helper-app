from __future__ import annotations

from typing import Any

# Weighting for UserGoal.progress (documented in README):
#   progress = 0.5 * normalized average confidence + 0.5 * average module step completion
CONFIDENCE_WEIGHT = 0.5
STEPS_WEIGHT = 0.5


def _confidence_component(confidence: dict[str, int], core_skills: list[dict[str, Any]]) -> float:
    if not core_skills:
        return 0.0
    scores = [confidence.get(s["id"], 3) for s in core_skills]  # default mid (3/5)
    avg = sum(scores) / len(scores)
    return (avg - 1) / 4  # map 1-5 -> 0-1


def _steps_component(tracking: dict[str, Any] | None, core_skills: list[dict[str, Any]]) -> float:
    if not core_skills:
        return 0.0
    modules = (tracking or {}).get("modules", {})
    ratios: list[float] = []
    for skill in core_skills:
        total = len(skill.get("whatToDo", []))
        if total == 0:
            ratios.append(0.0)
            continue
        done = len(modules.get(skill["id"], {}).get("completedSteps", []))
        ratios.append(min(done, total) / total)
    return sum(ratios) / len(ratios) if ratios else 0.0


def compute_progress(
    confidence: dict[str, int],
    catalog_goal: dict[str, Any],
    tracking: dict[str, Any] | None,
) -> int:
    core_skills = catalog_goal.get("coreSkills", [])
    conf = _confidence_component(confidence or {}, core_skills)
    steps = _steps_component(tracking, core_skills)
    return round((CONFIDENCE_WEIGHT * conf + STEPS_WEIGHT * steps) * 100)
