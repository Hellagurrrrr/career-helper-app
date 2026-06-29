"""Read-only catalog repository (goal catalog, jobs, alumni).

These are seeded reference tables (never written through the API). Each ``get_*``
loads a single row + its children; each ``list_*`` loads them all. Output keeps
the camelCase shape the schemas and matching consumers expect.

Migrating these off the in-memory mirror lets ``app/services/store.py`` drop the
whole ``Persistent*`` machinery -- the store is now just the connection + schema.
"""

from __future__ import annotations

import sqlite3
from typing import Any


def _skill_name(conn: sqlite3.Connection, skill_id: str, fallback: str = "") -> str:
    row = conn.execute("SELECT name FROM skills WHERE id = ?", (skill_id,)).fetchone()
    return row["name"] if row else fallback


# ----- goal catalog -----
def _row_to_catalog_goal(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    goal: dict[str, Any] = {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "color": row["color"],
        "defaultStatus": row["default_status"],
        "matchSignals": [
            r["signal"]
            for r in conn.execute(
                "SELECT signal FROM catalog_goal_match_signals WHERE catalog_goal_id = ? ORDER BY sort_order",
                (row["id"],),
            )
        ],
        "coreSkills": [],
    }
    for skill in conn.execute(
        "SELECT * FROM catalog_core_skills WHERE catalog_goal_id = ? ORDER BY sort_order",
        (row["id"],),
    ).fetchall():
        goal["coreSkills"].append(
            {
                "id": skill["id"],
                "name": skill["name"],
                "description": skill["description"],
                "defaultStatus": skill["default_status"],
                "whatToDo": [
                    r["text"]
                    for r in conn.execute(
                        "SELECT text FROM catalog_skill_steps WHERE skill_id = ? ORDER BY step_index",
                        (skill["id"],),
                    )
                ],
                "resources": [
                    {"title": r["title"], "type": r["type"], "url": r["url"]}
                    for r in conn.execute(
                        "SELECT * FROM catalog_skill_resources WHERE skill_id = ? ORDER BY resource_index",
                        (skill["id"],),
                    )
                ],
                "jobSkillKeywords": [
                    _skill_name(conn, r["skill_id"])
                    for r in conn.execute(
                        "SELECT skill_id FROM catalog_skill_job_keywords WHERE core_skill_id = ? ORDER BY sort_order",
                        (skill["id"],),
                    )
                ],
            }
        )
    return goal


def list_goal_catalog(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM catalog_goals ORDER BY sort_order, id").fetchall()
    return [_row_to_catalog_goal(conn, r) for r in rows]


def get_catalog_goal(conn: sqlite3.Connection, catalog_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM catalog_goals WHERE id = ?", (catalog_id,)).fetchone()
    return _row_to_catalog_goal(conn, row) if row else None


# ----- jobs -----
def _row_to_job(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    job = {
        "id": row["id"],
        "catalogGoalId": row["catalog_goal_id"],
        "title": row["title"],
        "company": row["company"],
        "companyTagline": row["company_tagline"],
        "location": row["location"],
        "type": row["type"],
        "salary": row["salary"],
        "posted": row["posted"],
        "skills": [
            _skill_name(conn, r["skill_id"])
            for r in conn.execute(
                "SELECT skill_id FROM job_skills WHERE job_id = ? ORDER BY sort_order", (row["id"],)
            )
        ],
        "partner": bool(row["partner"]),
        "exclusive": bool(row["exclusive"]),
        "applicationUrl": row["application_url"],
        "description": row["description"],
    }
    return {k: v for k, v in job.items() if v is not None}


def list_jobs(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM jobs ORDER BY id").fetchall()
    return [_row_to_job(conn, r) for r in rows]


def get_job(conn: sqlite3.Connection, job_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return _row_to_job(conn, row) if row else None


# ----- alumni -----
def _row_to_alumni(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    work = conn.execute(
        "SELECT * FROM alumni_work_experiences WHERE alumni_id = ? ORDER BY is_current DESC, sort_order LIMIT 1",
        (row["id"],),
    ).fetchone()
    edu = conn.execute(
        "SELECT * FROM alumni_education WHERE alumni_id = ? ORDER BY sort_order LIMIT 1", (row["id"],)
    ).fetchone()
    return {
        "id": row["id"],
        "firstName": row["first_name"],
        "lastInitial": row["last_initial"],
        "role": work["title"] if work else row["headline"] or "",
        "company": work["company"] if work else "",
        "industry": work["industry"] if work else "",
        "graduationYear": edu["graduation_year"] if edu and edu["graduation_year"] is not None else 0,
        "major": edu["major"] if edu else "",
        "university": edu["school"] if edu else "",
        "yearsExperience": 0,
        "bio": row["bio"],
        "expertise": [
            r["display_label"] or _skill_name(conn, r["skill_id"])
            for r in conn.execute(
                "SELECT * FROM alumni_expertise WHERE alumni_id = ? ORDER BY sort_order", (row["id"],)
            )
        ],
        "topics": [
            r["topic"]
            for r in conn.execute(
                "SELECT topic FROM alumni_topics WHERE alumni_id = ? ORDER BY sort_order", (row["id"],)
            )
        ],
        "responseTime": row["response_time"],
        "availability": row["availability"],
        "goalAlignment": [
            r["catalog_goal_id"]
            for r in conn.execute(
                "SELECT catalog_goal_id FROM alumni_goal_alignment WHERE alumni_id = ?", (row["id"],)
            )
        ],
        "avatarGradient": row["avatar_gradient"],
        "linkedinUrl": row["linkedin_url"],
    }


def list_alumni(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM alumni ORDER BY id").fetchall()
    return [_row_to_alumni(conn, r) for r in rows]


def get_alumni(conn: sqlite3.Connection, alumni_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM alumni WHERE id = ?", (alumni_id,)).fetchone()
    return _row_to_alumni(conn, row) if row else None
