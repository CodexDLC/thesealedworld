"""AI behaviour profiles for simulation pacing.

Behaviour profile is separate from build/archetype. It controls how quickly an
actor places queued exchange moves in live-like simulations.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class BehaviorProfile(StrEnum):
    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"
    DEFENSIVE = "defensive"

    @classmethod
    def coerce(cls, value: str | None) -> BehaviorProfile:
        normalized = str(value or "").strip().lower()
        for member in cls:
            if member.value == normalized:
                return member
        return cls.BALANCED


@dataclass(frozen=True, slots=True)
class BehaviorProfileSettings:
    decision_interval_multiplier: float
    decisions_per_tick: int


BEHAVIOR_PROFILE_SETTINGS: dict[BehaviorProfile, BehaviorProfileSettings] = {
    BehaviorProfile.AGGRESSIVE: BehaviorProfileSettings(decision_interval_multiplier=0.2, decisions_per_tick=5),
    BehaviorProfile.BALANCED: BehaviorProfileSettings(decision_interval_multiplier=0.5, decisions_per_tick=3),
    BehaviorProfile.DEFENSIVE: BehaviorProfileSettings(decision_interval_multiplier=1.0, decisions_per_tick=1),
}


def behavior_settings(value: str | None) -> BehaviorProfileSettings:
    return BEHAVIOR_PROFILE_SETTINGS[BehaviorProfile.coerce(value)]


__all__ = ["BEHAVIOR_PROFILE_SETTINGS", "BehaviorProfile", "BehaviorProfileSettings", "behavior_settings"]
