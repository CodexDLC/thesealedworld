from pydantic import BaseModel, Field


class ScenarioRewardsDTO(BaseModel):
    items: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    attribute_bonuses: dict[str, int] = Field(default_factory=dict)


class ScenarioFinalizeResult(BaseModel):
    rewards: ScenarioRewardsDTO = Field(default_factory=ScenarioRewardsDTO)
