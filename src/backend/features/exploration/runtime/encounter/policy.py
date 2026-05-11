from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from src.backend.features.exploration.dto.config import ExplorationConfig
from src.backend.features.exploration.runtime.encounter.modes import EncounterMode
from src.shared.schemas.exploration import DetectionStatus


@dataclass(frozen=True, slots=True)
class EncounterRoll:
    discovery_type: str
    difficulty: str
    status: DetectionStatus


class EncounterPolicy:
    """Shared encounter policy. Modes supply weights; discoveries build payloads."""

    DEFAULT_GEAR_SCORE_DIVISOR = 10.0

    DISCOVERY_WEIGHTS: dict[EncounterMode, dict[str, float]] = {
        EncounterMode.TRAVEL: {"monster": 100.0, "rift": 0.0, "merchant": 0.0, "resource": 0.0},
        EncounterMode.TERRITORY_SCOUTING: {"monster": 70.0, "rift": 10.0, "merchant": 10.0, "resource": 10.0},
        EncounterMode.AUTO_SCOUTING: {"monster": 55.0, "rift": 15.0, "merchant": 10.0, "resource": 20.0},
    }

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()  # nosec B311

    def is_safe_context(self, flags: dict[str, Any], anchor_influence: dict[str, Any] | None = None) -> bool:
        del anchor_influence
        if flags.get("is_safe_zone", False):
            return True
        try:
            return float(flags.get("threat_tier", 1)) <= 0
        except (TypeError, ValueError):
            return False

    def should_roll(self, *, mode: EncounterMode, trigger: str) -> bool:
        if mode == EncounterMode.TRAVEL:
            chance = ExplorationConfig.CHANCE_COMBAT_BASE
        elif trigger == "search":
            chance = ExplorationConfig.CHANCE_COMBAT_SEARCH
        else:
            chance = ExplorationConfig.CHANCE_COMBAT_BASE
        return self._rng.random() < float(chance)

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

    def monster_budget(self, gear_score: float) -> float:
        return max(1.0, round(max(0.0, float(gear_score)) / self.DEFAULT_GEAR_SCORE_DIVISOR, 2))

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
