from __future__ import annotations

from typing import Any

from src.backend.core.calculators.skill_progression_calculator import (
    SkillProgressionBatchInput,
    SkillProgressionCalculator,
    SkillProgressionEntry,
)
from src.backend.features.game_catalog.skills.services import SkillCatalogService


class ExplorationExperienceService:
    """Projects exploration action power into skill XP rewards."""

    def __init__(self, *, catalog: SkillCatalogService | None = None) -> None:
        self.catalog = catalog or SkillCatalogService()

    def calculate_rewards(
        self,
        *,
        action_power_by_skill: dict[str, float],
        current_skills: dict[str, float],
        attributes: dict[str, float],
        global_rate: float | None = None,
    ) -> dict[str, float]:
        entries: dict[str, SkillProgressionEntry] = {}
        for skill_key, action_power in action_power_by_skill.items():
            skill = self.catalog.get(skill_key)
            if skill is None or action_power <= 0:
                continue
            entries[skill_key] = SkillProgressionEntry(
                skill=skill,
                attributes=attributes,
                current_skill=float(current_skills.get(skill_key, 0.0) or 0.0),
                action_power=action_power,
            )
        if global_rate is not None:
            batch_input = SkillProgressionBatchInput(entries=entries, global_rate=global_rate)
        else:
            batch_input = SkillProgressionBatchInput(entries=entries)
        return SkillProgressionCalculator.calculate(batch_input)


def flat_attribute_snapshot(raw: Any) -> dict[str, float]:
    attributes = raw if isinstance(raw, dict) else {}
    flat: dict[str, float] = {}
    for key, value in attributes.items():
        if isinstance(value, dict):
            base = _number(value.get("base"))
            source = sum(_number(item) for item in _dict(value.get("source")).values())
            temp = sum(_number(item) for item in _dict(value.get("temp")).values())
            flat[str(key)] = base + source + temp
        else:
            flat[str(key)] = _number(value)
    return flat


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _number(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
