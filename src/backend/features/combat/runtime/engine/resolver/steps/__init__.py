"""Resolver step classes (one per pipeline stage).

Each step is a stateless singleton with ``run(atk, def_, ctx, res)``. The
orchestrator drives them in fixed order with explicit early-return; this is
an imperative pipeline, not a registry/loop. Damage decomposition lives in
``steps/damage/`` (introduced in Phase 5).
"""

from .accuracy import AccuracyStep, accuracy_step
from .block import BlockStep, block_step
from .counter_check import CounterCheckStep, counter_check_step
from .crit import CritStep, crit_step
from .evasion import EvasionStep, evasion_step
from .healing import HealingStep, healing_step
from .parry import ParryStep, parry_step
from .ranged_position_defense import RangedPositionDefenseStep, ranged_position_defense_step

__all__ = [
    "AccuracyStep",
    "BlockStep",
    "CounterCheckStep",
    "CritStep",
    "EvasionStep",
    "HealingStep",
    "ParryStep",
    "RangedPositionDefenseStep",
    "accuracy_step",
    "block_step",
    "counter_check_step",
    "crit_step",
    "evasion_step",
    "healing_step",
    "parry_step",
    "ranged_position_defense_step",
]
