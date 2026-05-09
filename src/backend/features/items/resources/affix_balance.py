from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import Literal

AFFIX_TIER_MULTIPLIERS: dict[int, float] = {
    0: 0.80,
    1: 1.00,
    2: 1.35,
    3: 1.90,
    4: 2.75,
    5: 4.00,
    6: 5.80,
    7: 8.50,
}

GLOBAL_AFFIX_STEPS = 5
DEFAULT_AFFIX_STEP_SPREAD = 0.05
AFFIX_ROUND_DIGITS = 4
AffixRoundingMode = Literal["decimal", "floor_int", "round_int"]


@dataclass(frozen=True, slots=True)
class AffixRollProfile:
    step_spread: float = DEFAULT_AFFIX_STEP_SPREAD
    rounding: AffixRoundingMode = "decimal"
    round_digits: int = AFFIX_ROUND_DIGITS


@dataclass(frozen=True, slots=True)
class AffixBalanceBreakdown:
    tier: int
    tier_multiplier: float
    step_count: int
    step_roll_min: float
    step_roll_max: float
    step_roll_multiplier: float
    step_roll_total: float
    power_multiplier: float
    rounding: AffixRoundingMode


DEFAULT_AFFIX_ROLL_PROFILE = AffixRollProfile()
ATTRIBUTE_AFFIX_ROLL_PROFILE = AffixRollProfile(step_spread=0.10, rounding="floor_int", round_digits=0)


def calculate_affix_value(
    base_value: float,
    *,
    tier: int,
    roll_profile: AffixRollProfile | None = None,
    roll_quality: float = 0.5,
) -> float:
    profile = roll_profile or DEFAULT_AFFIX_ROLL_PROFILE
    breakdown = affix_balance_breakdown(tier=tier, roll_profile=profile, roll_quality=roll_quality)
    return _round_affix_value(float(base_value) * breakdown.power_multiplier, profile)


def affix_balance_breakdown(
    *,
    tier: int,
    roll_profile: AffixRollProfile | None = None,
    roll_quality: float = 0.5,
) -> AffixBalanceBreakdown:
    profile = roll_profile or DEFAULT_AFFIX_ROLL_PROFILE
    safe_tier = _clamp_level(tier)
    tier_multiplier = AFFIX_TIER_MULTIPLIERS[safe_tier]
    step_roll_min = max(0.0, 1.0 - profile.step_spread)
    step_roll_max = 1.0 + profile.step_spread
    step_roll_multiplier = step_roll_min + ((step_roll_max - step_roll_min) * _clamp_roll_quality(roll_quality))
    step_roll_total = GLOBAL_AFFIX_STEPS * step_roll_multiplier
    power_multiplier = tier_multiplier * step_roll_total
    return AffixBalanceBreakdown(
        tier=safe_tier,
        tier_multiplier=tier_multiplier,
        step_count=GLOBAL_AFFIX_STEPS,
        step_roll_min=round(step_roll_min, AFFIX_ROUND_DIGITS),
        step_roll_max=round(step_roll_max, AFFIX_ROUND_DIGITS),
        step_roll_multiplier=round(step_roll_multiplier, AFFIX_ROUND_DIGITS),
        step_roll_total=round(step_roll_total, AFFIX_ROUND_DIGITS),
        power_multiplier=round(power_multiplier, AFFIX_ROUND_DIGITS),
        rounding=profile.rounding,
    )


def _clamp_level(value: int) -> int:
    return max(0, min(7, int(value)))


def _clamp_roll_quality(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _round_affix_value(value: float, profile: AffixRollProfile) -> float:
    if profile.rounding == "floor_int":
        return float(floor(value))
    if profile.rounding == "round_int":
        return float(round(value))
    return round(value, profile.round_digits)


__all__ = [
    "AFFIX_TIER_MULTIPLIERS",
    "ATTRIBUTE_AFFIX_ROLL_PROFILE",
    "AffixBalanceBreakdown",
    "AffixRollProfile",
    "DEFAULT_AFFIX_ROLL_PROFILE",
    "DEFAULT_AFFIX_STEP_SPREAD",
    "GLOBAL_AFFIX_STEPS",
    "affix_balance_breakdown",
    "calculate_affix_value",
]
