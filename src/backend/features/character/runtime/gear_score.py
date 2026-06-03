from __future__ import annotations

from typing import Any

from src.backend.core.calculators.stats_waterfall_calculator import StatsWaterfallCalculator
from src.backend.features.character.dto.modifiers import CombatModifiersDTO
from src.backend.features.character.runtime.combat_actor_input import CharacterCombatActorInputBuilder
from src.backend.features.character.runtime.combat_math_model import CharacterCombatMathModelBuilder
from src.backend.features.character.runtime.rules.base_power_assembler import BasePowerAssembler
from src.backend.features.character.runtime.rules.gear_score import (
    GEAR_SCORE_BASE,
    GEAR_SCORE_BASELINES,
    GEAR_SCORE_CAPS,
    GEAR_SCORE_GROUPS,
    GEAR_SCORE_MINIMUM,
    GEAR_SCORE_WEIGHTS,
)


class CharacterGearScoreCalculator:
    """Calculates gear score from combat-effective modifiers after base-power assembly."""

    def __init__(self, math_model: CharacterCombatMathModelBuilder | None = None) -> None:
        self.math_model = math_model or CharacterCombatMathModelBuilder()

    def calculate_from_active_character(self, active_character: dict[str, Any]) -> int:
        actor_input = CharacterCombatActorInputBuilder(self.math_model).build_input(active_character)
        return self.calculate_from_raw(
            actor_input["raw"],
            skills=actor_input["skills"],
            loadout=actor_input["loadout"],
        )

    def calculate_breakdown_from_active_character(self, active_character: dict[str, Any]) -> dict[str, float | int]:
        actor_input = CharacterCombatActorInputBuilder(self.math_model).build_input(active_character)
        return self.calculate_breakdown_from_raw(
            actor_input["raw"],
            skills=actor_input["skills"],
            loadout=actor_input["loadout"],
        )

    @staticmethod
    def calculate_from_raw(
        raw: dict[str, Any],
        *,
        skills: dict[str, Any] | None = None,
        loadout: dict[str, Any] | None = None,
    ) -> int:
        calculated, _ = StatsWaterfallCalculator.calculate_waterfall(raw)
        CharacterGearScoreCalculator._apply_combat_power_projection(calculated, skills=skills, loadout=loadout)
        return CharacterGearScoreCalculator.calculate_from_calculated(calculated)

    @staticmethod
    def calculate_from_calculated(calculated: dict[str, Any]) -> int:
        default_modifiers = CombatModifiersDTO().model_dump(mode="json")
        score = GEAR_SCORE_BASE
        for key, weight in GEAR_SCORE_WEIGHTS.items():
            value = CharacterGearScoreCalculator._float_value(calculated.get(key, default_modifiers.get(key)))
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
    def calculate_breakdown_from_raw(
        raw: dict[str, Any],
        *,
        skills: dict[str, Any] | None = None,
        loadout: dict[str, Any] | None = None,
    ) -> dict[str, float | int]:
        calculated, _ = StatsWaterfallCalculator.calculate_waterfall(raw)
        CharacterGearScoreCalculator._apply_combat_power_projection(calculated, skills=skills, loadout=loadout)
        return CharacterGearScoreCalculator.calculate_breakdown_from_calculated(calculated)

    @staticmethod
    def calculate_breakdown_from_calculated(calculated: dict[str, Any]) -> dict[str, float | int]:
        default_modifiers = CombatModifiersDTO().model_dump(mode="json")
        group_by_key = {key: group for group, keys in GEAR_SCORE_GROUPS.items() for key in keys}
        groups = {group: 0.0 for group in GEAR_SCORE_GROUPS}
        for key, weight in GEAR_SCORE_WEIGHTS.items():
            value = CharacterGearScoreCalculator._float_value(calculated.get(key, default_modifiers.get(key)))
            if value is None:
                continue
            baseline = GEAR_SCORE_BASELINES.get(key, 0.0)
            effective = value - baseline
            cap = GEAR_SCORE_CAPS.get(key)
            if cap is not None:
                effective = max(-cap, min(effective, cap))
            group = group_by_key.get(key, "utility")
            groups[group] = groups.get(group, 0.0) + effective * weight

        display_groups = {group: round(max(0.0, value), 3) for group, value in groups.items()}
        total = CharacterGearScoreCalculator.calculate_from_calculated(calculated)
        return {
            "total": total,
            "offense": display_groups.get("offense", 0.0),
            "defense": display_groups.get("defense", 0.0),
            "resources": display_groups.get("resources", 0.0),
            "skills": 0.0,
            "utility": display_groups.get("utility", 0.0),
        }

    @staticmethod
    def _float_value(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _apply_combat_power_projection(
        calculated: dict[str, Any],
        *,
        skills: dict[str, Any] | None,
        loadout: dict[str, Any] | None,
    ) -> None:
        if not skills or not loadout:
            return
        layout = loadout.get("layout")
        if not isinstance(layout, dict):
            return
        BasePowerAssembler.apply_to_values(calculated, loadout_layout=layout, skills=skills)


__all__ = ["CharacterGearScoreCalculator"]
