from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.common import CamelModel


class SkillResource(CamelModel):
    title: str
    type: str
    url: str


class CoreSkill(CamelModel):
    id: str
    name: str
    description: str
    default_status: str
    what_to_do: list[str] = Field(default_factory=list)
    resources: list[SkillResource] = Field(default_factory=list)
    job_skill_keywords: list[str] = Field(default_factory=list)


class CatalogGoal(CamelModel):
    id: str
    title: str
    description: str
    color: str
    match_signals: list[str] = Field(default_factory=list)
    default_status: Literal["active", "exploring"]
    core_skills: list[CoreSkill] = Field(default_factory=list)


class UserGoal(CamelModel):
    id: str
    catalog_id: str
    title: str
    description: str
    color: str
    status: Literal["active", "exploring"]
    progress: int
    last_updated: str
    created_at: int
    confidence: dict[str, int] = Field(default_factory=dict)
    sort_order: int


class CreateGoalRequest(CamelModel):
    catalog_id: str


class UpdateGoalRequest(CamelModel):
    status: Literal["active", "exploring"] | None = None
    confidence: dict[str, int] | None = None


class ReorderGoalsRequest(CamelModel):
    goal_ids: list[str]
