from __future__ import annotations

from typing import Any


def _norm(values: list[str]) -> set[str]:
    return {v.strip().lower() for v in values if v and v.strip()}


def match_score(profile_skills: list[str], target_skills: list[str]) -> int:
    """Simple overlap-based match score in 0-100.

    Mock rule: share of the target's skills the candidate already has, with a
    small floor so nothing shows 0.
    """
    target = _norm(target_skills)
    if not target:
        return 50
    have = _norm(profile_skills)
    overlap = len(have & target) / len(target)
    return max(20, round(overlap * 100))


def catalog_match_score(profile: dict[str, Any] | None, catalog_goal: dict[str, Any]) -> int:
    """Score a catalog goal against the profile (skills + major signals)."""
    profile = profile or {}
    signals = list(catalog_goal.get("matchSignals", []))
    candidate = list(profile.get("skills", []))
    education = profile.get("education") or []
    if education:
        candidate.append(education[0].get("major", ""))
    return match_score(candidate, signals)


def sort_catalog_goals(profile: dict[str, Any] | None, catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return catalog goals sorted by descending match (use-case NG-01)."""
    return sorted(catalog, key=lambda g: catalog_match_score(profile, g), reverse=True)


def alumni_match(profile: dict[str, Any] | None, user_goal_catalog_ids: set[str], alum: dict[str, Any]) -> int:
    """Higher score = better alumni recommendation for the user's goals."""
    score = 0
    if user_goal_catalog_ids & set(alum.get("goalAlignment", [])):
        score += 100
    profile_skills = _norm((profile or {}).get("skills", []))
    score += len(profile_skills & _norm(alum.get("expertise", []))) * 10
    return score


def sort_alumni(
    profile: dict[str, Any] | None,
    user_goal_catalog_ids: set[str],
    alumni: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return sorted(
        alumni,
        key=lambda a: alumni_match(profile, user_goal_catalog_ids, a),
        reverse=True,
    )
