from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

GLOBAL_BASE_RATE = 0.000005
GLOBAL_BASE_WALL = 100.0


class SkillProgressionInput(BaseModel):
    skill: Any
    attributes: dict[str, float]
    current_skill: float = Field(ge=0.0, le=1.0)
    action_power: float = Field(default=1.0, ge=0.0)


class SkillProgressionResult(BaseModel):
    current_skill: float
    delta: float
    next_skill: float
    base_power: float
    effective_rate: float
    effective_wall: float
    resistance: float


def calculate_skill_delta(payload: SkillProgressionInput) -> SkillProgressionResult:
    base_power = _calculate_base_power(payload.skill, payload.attributes) * payload.action_power
    effective_rate = GLOBAL_BASE_RATE * payload.skill.rate_mod
    effective_wall = GLOBAL_BASE_WALL * payload.skill.wall_mod
    resistance = 1.0 + (payload.current_skill * effective_wall)
    delta = (base_power * effective_rate) / resistance if resistance > 0 else 0.0
    next_skill = min(1.0, payload.current_skill + delta)
    return SkillProgressionResult(
        current_skill=payload.current_skill,
        delta=delta,
        next_skill=next_skill,
        base_power=base_power,
        effective_rate=effective_rate,
        effective_wall=effective_wall,
        resistance=resistance,
    )


def _calculate_base_power(skill: Any, attributes: dict[str, float]) -> float:
    return sum(float(attributes.get(stat_key, 0.0)) * weight for stat_key, weight in skill.stat_weights.items())
