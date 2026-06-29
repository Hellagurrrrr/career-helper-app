"""Profiles repository (aggregate root: ``profiles`` + 5 child tables).

``get``/``save``/``delete`` operate on a single user's profile. ``save`` replaces
just that user's ``profiles`` row -- the education/internship/project/skill/
coursework children cascade via FK -- instead of the legacy "DELETE all 6 tables,
reinsert everyone" rewrite.

Like the onboarding repo, the profile working-dict keeps the camelCase shape the
schema (``app.schemas.profile.Profile``) and the matching consumers
(``mock_match``/``ai_service``) already use; only ``updatedAt`` is multi-word
(child item keys are single words), and the repo maps it to/from the snake_case
columns.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any


def _normalize_skill_text(raw: str) -> str:
    # Mirrors the catalog seeder's skill normalizer so profile skills resolve to
    # the same skill_aliases entries. (Temporary duplication until the store is gone.)
    text = raw.strip().lower()
    text = re.sub(r"[._/+-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if text.endswith(" js"):
        text = text[:-3].strip()
    return text


def get(conn: sqlite3.Connection, user_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
    if row is None:
        return None
    profile: dict[str, Any] = {
        "name": row["name"],
        "education": [],
        "internships": [],
        "projects": [],
        "skills": [],
        "coursework": [],
        "updatedAt": row["updated_at"],
    }
    for r in conn.execute(
        "SELECT * FROM profile_education WHERE user_id = ? ORDER BY sort_order", (user_id,)
    ):
        profile["education"].append(
            {
                "degree": r["degree"],
                "school": r["school"],
                "major": r["major"],
                "grade": r["grade"],
                "start": r["start"],
                "end": r["end"],
            }
        )
    for r in conn.execute(
        "SELECT * FROM profile_internships WHERE user_id = ? ORDER BY sort_order", (user_id,)
    ):
        profile["internships"].append(
            {
                "title": r["title"],
                "company": r["company"],
                "start": r["start"],
                "end": r["end"],
                "description": r["description"],
            }
        )
    for r in conn.execute(
        "SELECT * FROM profile_projects WHERE user_id = ? ORDER BY sort_order", (user_id,)
    ):
        profile["projects"].append(
            {
                "title": r["title"],
                "start": r["start"],
                "end": r["end"],
                "description": r["description"],
            }
        )
    for r in conn.execute(
        "SELECT raw_text FROM profile_skills WHERE user_id = ? ORDER BY sort_order", (user_id,)
    ):
        profile["skills"].append(r["raw_text"])
    for r in conn.execute(
        "SELECT course FROM profile_coursework WHERE user_id = ? ORDER BY sort_order", (user_id,)
    ):
        profile["coursework"].append(r["course"])
    return profile


def save(conn: sqlite3.Connection, user_id: str, profile: dict[str, Any] | None) -> None:
    """Persist a user's profile aggregate (children replaced via cascade)."""
    conn.execute("DELETE FROM profiles WHERE user_id = ?", (user_id,))
    if not profile:
        return
    conn.execute(
        "INSERT INTO profiles(user_id, name, updated_at) VALUES(?, ?, ?)",
        (user_id, profile.get("name", ""), profile.get("updatedAt", 0)),
    )
    for idx, edu in enumerate(profile.get("education", [])):
        conn.execute(
            "INSERT INTO profile_education(user_id, sort_order, degree, school, major, grade, start, end) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, idx, edu.get("degree", ""), edu.get("school", ""), edu.get("major", ""),
             edu.get("grade"), edu.get("start", ""), edu.get("end")),
        )
    for idx, intern in enumerate(profile.get("internships", [])):
        conn.execute(
            "INSERT INTO profile_internships(user_id, sort_order, title, company, start, end, description) "
            "VALUES(?, ?, ?, ?, ?, ?, ?)",
            (user_id, idx, intern.get("title", ""), intern.get("company", ""), intern.get("start", ""),
             intern.get("end"), intern.get("description", "")),
        )
    for idx, project in enumerate(profile.get("projects", [])):
        conn.execute(
            "INSERT INTO profile_projects(user_id, sort_order, title, start, end, description) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            (user_id, idx, project.get("title", ""), project.get("start", ""),
             project.get("end"), project.get("description", "")),
        )
    for idx, skill in enumerate(profile.get("skills", [])):
        normalized = _normalize_skill_text(skill)
        row = conn.execute(
            "SELECT skill_id FROM skill_aliases WHERE normalized_alias = ?", (normalized,)
        ).fetchone()
        skill_id = row["skill_id"] if row else None
        confidence = 1.0 if skill_id else 0.0
        conn.execute(
            "INSERT OR REPLACE INTO profile_skills"
            "(user_id, raw_text, normalized_text, skill_id, match_confidence, source, sort_order) "
            "VALUES(?, ?, ?, ?, ?, 'user', ?)",
            (user_id, skill, normalized, skill_id, confidence, idx),
        )
    for idx, course in enumerate(profile.get("coursework", [])):
        conn.execute(
            "INSERT OR REPLACE INTO profile_coursework(user_id, course, sort_order) VALUES(?, ?, ?)",
            (user_id, course, idx),
        )


def delete(conn: sqlite3.Connection, user_id: str) -> None:
    """Delete a user's profile (child rows cascade via FK)."""
    conn.execute("DELETE FROM profiles WHERE user_id = ?", (user_id,))
