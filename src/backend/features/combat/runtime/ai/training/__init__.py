"""Offline policy training for combat AI.

MVP: deterministic evolutionary search over a synthetic scoring environment.
No Redis, ARQ, or HTTP dependencies — this package is importable standalone.
"""

from src.backend.features.combat.runtime.ai.training.environment import (
    EvalResult,
    ScoringEnvironment,
)
from src.backend.features.combat.runtime.ai.training.evolution import TrainingRun, evolve
from src.backend.features.combat.runtime.ai.training.scenarios import (
    SyntheticScenario,
    default_scenario_set,
)
from src.backend.features.combat.runtime.ai.training.train_policy import TrainArgs, train

__all__ = [
    "EvalResult",
    "ScoringEnvironment",
    "SyntheticScenario",
    "TrainArgs",
    "TrainingRun",
    "default_scenario_set",
    "evolve",
    "train",
]
