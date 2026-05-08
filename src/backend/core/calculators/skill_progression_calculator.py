from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

GLOBAL_BASE_RATE = 0.000005
GLOBAL_BASE_WALL = 100.0


class SkillProgressionEntry(BaseModel):
    skill: Any | None = None
    attributes: dict[str, float] = Field(default_factory=dict)
    current_skill: float = Field(default=0.0, ge=0.0)
    action_power: float = Field(default=1.0, ge=0.0)
    base_power: float | None = Field(default=None, ge=0.0)
    rate_mod: float | None = None
    wall_mod: float | None = None


class SkillProgressionBatchInput(BaseModel):
    entries: dict[str, SkillProgressionEntry] = Field(default_factory=dict)
    global_rate: float = GLOBAL_BASE_RATE
    global_wall: float = GLOBAL_BASE_WALL
    precision: int = 4


class SkillProgressionCalculator:
    @classmethod
    def calculate(cls, payload: SkillProgressionBatchInput) -> dict[str, float]:
        result: dict[str, float] = {}
        for skill_key, entry in payload.entries.items():
            delta = cls.calculate_delta(
                entry,
                global_rate=payload.global_rate,
                global_wall=payload.global_wall,
            )
            rounded = round(delta, payload.precision)
            if rounded > 0:
                result[skill_key] = rounded
        return result

    @classmethod
    def calculate_delta(
        cls,
        entry: SkillProgressionEntry,
        *,
        global_rate: float = GLOBAL_BASE_RATE,
        global_wall: float = GLOBAL_BASE_WALL,
    ) -> float:
        base_power = cls.calculate_base_power(entry)
        rate_mod = entry.rate_mod if entry.rate_mod is not None else cls._skill_number(entry.skill, "rate_mod", 1.0)
        wall_mod = entry.wall_mod if entry.wall_mod is not None else cls._skill_number(entry.skill, "wall_mod", 1.0)
        effective_wall = global_wall * wall_mod
        resistance = 1.0 + (entry.current_skill * effective_wall)
        if resistance <= 0:
            return 0.0
        return (base_power * global_rate * rate_mod) / resistance

    @classmethod
    def calculate_base_power(cls, entry: SkillProgressionEntry) -> float:
        if entry.base_power is not None:
            return entry.base_power * entry.action_power
        if entry.skill is None:
            return 0.0
        weighted = sum(
            float(entry.attributes.get(stat_key, 0.0)) * float(weight)
            for stat_key, weight in cls._skill_weights(entry.skill).items()
        )
        return weighted * entry.action_power

    @staticmethod
    def _skill_weights(skill: Any) -> dict[str, float]:
        raw = getattr(skill, "stat_weights", None)
        return raw if isinstance(raw, dict) else {}

    @staticmethod
    def _skill_number(skill: Any, field_name: str, default: float) -> float:
        try:
            return float(getattr(skill, field_name, default))
        except (TypeError, ValueError):
            return default


__all__ = [
    "GLOBAL_BASE_RATE",
    "GLOBAL_BASE_WALL",
    "SkillProgressionBatchInput",
    "SkillProgressionCalculator",
    "SkillProgressionEntry",
]
