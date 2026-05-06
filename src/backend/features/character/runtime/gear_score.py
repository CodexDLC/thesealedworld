from __future__ import annotations

from typing import Any

from src.backend.core.calculators.stats_waterfall_calculator import StatsWaterfallCalculator
from src.backend.features.character.dto.modifiers import CombatModifiersDTO
from src.backend.features.character.runtime.combat_math_model import CharacterCombatMathModelBuilder
from src.backend.features.character.runtime.rules.gear_score import (
    GEAR_SCORE_BASE,
    GEAR_SCORE_BASELINES,
    GEAR_SCORE_CAPS,
    GEAR_SCORE_MINIMUM,
    GEAR_SCORE_WEIGHTS,
)


class CharacterGearScoreCalculator:
    """Calculates character gear score from waterfall-calculated combat modifiers."""

    def __init__(self, math_model: CharacterCombatMathModelBuilder | None = None) -> None:
        self.math_model = math_model or CharacterCombatMathModelBuilder()

    def calculate_from_active_character(self, active_character: dict[str, Any]) -> int:
        raw = self.math_model.build_raw(
            attributes=active_character.get("attributes") or {},
            items=active_character.get("items") or {},
            skills=active_character.get("skills") or {},
        )
        return self.calculate_from_raw(raw)

    @staticmethod
    def calculate_from_raw(raw: dict[str, Any]) -> int:
        calculated, _ = StatsWaterfallCalculator.calculate_waterfall(raw)
        return CharacterGearScoreCalculator.calculate_from_calculated(calculated)

    @staticmethod
    def calculate_from_calculated(calculated: dict[str, Any]) -> int:
        modifiers = CombatModifiersDTO(**calculated).model_dump(mode="json")
        score = GEAR_SCORE_BASE
        for key, weight in GEAR_SCORE_WEIGHTS.items():
            value = CharacterGearScoreCalculator._float_value(modifiers.get(key))
            if value is None:
                continue
            baseline = GEAR_SCORE_BASELINES.get(key, 0.0)
            effective = value - baseline
            cap = GEAR_SCORE_CAPS.get(key)
            if cap is not None:
                effective = max(-cap, min(effective, cap))
            score += effective * weight

        return max(GEAR_SCORE_MINIMUM, int(round(score)))

    @staticmethod
    def _float_value(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


__all__ = ["CharacterGearScoreCalculator"]
