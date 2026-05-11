from typing import Any

from pydantic import BaseModel, Field

from src.shared.enums import CoreDomain


class ScenarioRewardsDTO(BaseModel):
    items: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    skill_initial_xp: float | None = None
    attribute_bonuses: dict[str, int] = Field(default_factory=dict)


class ScenarioFinalizeResult(BaseModel):
    rewards: ScenarioRewardsDTO = Field(default_factory=ScenarioRewardsDTO)
    target_state: CoreDomain = CoreDomain.EXPLORATION
    transition_reason: str = "scenario_finalized"
    combat_id: str | None = None
    location_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
