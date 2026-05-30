from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from src.backend.features.exploration.game_config import ExplorationConfig
from src.backend.features.exploration.runtime.encounter.modes import EncounterMode
from src.backend.features.exploration.runtime.tunables import current_tunables
from src.shared.schemas.exploration import DetectionStatus


@dataclass(frozen=True, slots=True)
class EncounterRoll:
    discovery_type: str
    difficulty: str
    status: DetectionStatus


class EncounterPolicy:
    """Shared encounter policy. Modes supply weights; discoveries build payloads."""

    DISCOVERY_WEIGHTS: dict[EncounterMode, dict[str, float]] = {
        EncounterMode.TRAVEL: {"monster": 100.0, "rift": 0.0, "merchant": 0.0, "resource": 0.0},
        EncounterMode.TERRITORY_SCOUTING: {"monster": 70.0, "rift": 10.0, "merchant": 10.0, "resource": 10.0},
        EncounterMode.AUTO_SCOUTING: {"monster": 55.0, "rift": 15.0, "merchant": 10.0, "resource": 20.0},
    }

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()  # nosec B311

    def is_safe_context(self, flags: dict[str, Any], anchor_influence: dict[str, Any] | None = None) -> bool:
        del anchor_influence
        return bool(flags.get("system_connect") or flags.get("is_safe_zone", False))

    def should_roll(
        self,
        *,
        mode: EncounterMode,
        trigger: str,
        scouting_skill: float = 0.0,
        hunting_skill: float = 0.0,
        pathfinder_skill: float = 0.0,
    ) -> bool:
        tunables = current_tunables()
        if mode == EncounterMode.TRAVEL:
            chance = tunables.chance_combat_base
        elif trigger == "search":
            chance = tunables.chance_combat_search
        else:
            chance = tunables.chance_combat_base
        chance = self.encounter_chance(
            base_chance=chance,
            trigger=trigger,
            scouting_skill=scouting_skill,
            hunting_skill=hunting_skill,
            pathfinder_skill=pathfinder_skill,
        )
        return self._rng.random() < chance

    @staticmethod
    def encounter_chance(
        *,
        base_chance: float,
        trigger: str,
        scouting_skill: float = 0.0,
        hunting_skill: float = 0.0,
        pathfinder_skill: float = 0.0,
    ) -> float:
        del trigger, scouting_skill, hunting_skill, pathfinder_skill
        return max(0.0, min(1.0, float(base_chance)))

    def roll(self, *, mode: EncounterMode, tier: int, scouting_skill: float) -> EncounterRoll:
        difficulty = self._weighted_choice(
            {
                key: float(value)
                for key, value in ExplorationConfig.TIER_DIFFICULTY_WEIGHTS.get(
                    tier,
                    ExplorationConfig.TIER_DIFFICULTY_WEIGHTS[1],
                ).items()
            }
        )
        discovery_type = self._weighted_choice(self.DISCOVERY_WEIGHTS[mode])
        status = self.detection_status(tier=tier, difficulty=difficulty, scouting_skill=scouting_skill)
        return EncounterRoll(discovery_type=discovery_type, difficulty=difficulty, status=status)

    def monster_budget(self, gear_score: float, *, hunting_skill: float = 0.0) -> float:
        base_budget = max(0.0, float(gear_score))
        normalized_hunting = _normalized_skill(hunting_skill)
        variance = (1.0 - normalized_hunting) * 0.45
        if variance <= 0:
            return max(1.0, round(base_budget, 2))
        multiplier = self._rng.uniform(1.0 - variance, 1.0 + variance)
        return max(1.0, round(base_budget * multiplier, 2))

    def detection_status(self, *, tier: int, difficulty: str, scouting_skill: float) -> DetectionStatus:
        diff_mod = ExplorationConfig.DETECTION_MODIFIERS.get(difficulty, 0)
        loc_difficulty = (tier * 10) + diff_mod
        scouting_score = float(scouting_skill) * 100 if 0.0 <= float(scouting_skill) <= 1.0 else float(scouting_skill)
        diff = scouting_score - loc_difficulty + self._rng.uniform(-5, 5)
        return DetectionStatus.DETECTED if diff >= 0 else DetectionStatus.AMBUSH

    def _weighted_choice(self, weights: dict[str, float]) -> str:
        positive = [(key, max(0.0, float(weight))) for key, weight in weights.items()]
        total = sum(weight for _, weight in positive)
        if total <= 0:
            return next(iter(weights))
        marker = self._rng.uniform(0, total)
        current = 0.0
        for key, weight in positive:
            current += weight
            if marker <= current:
                return key
        return positive[-1][0]


def _normalized_skill(value: Any) -> float:
    try:
        raw = float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if raw > 1.0:
        raw /= 100.0
    return max(0.0, min(1.0, raw))
