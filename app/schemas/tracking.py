from __future__ import annotations

from pydantic import Field

from app.schemas.common import CamelModel


class ModuleTracking(CamelModel):
    completed_steps: list[int] = Field(default_factory=list)
    consumed_resources: list[int] = Field(default_factory=list)
    steps_completed_since_rerate: int = 0
    rerate_dismissed: bool = False


class GoalTracking(CamelModel):
    modules: dict[str, ModuleTracking] = Field(default_factory=dict)
    week_started_at: int
    week_focus: list[str] = Field(default_factory=list)


class StepToggleRequest(CamelModel):
    completed: bool


class ResourceToggleRequest(CamelModel):
    consumed: bool


class WeekFocusRequest(CamelModel):
    week_focus: list[str]
