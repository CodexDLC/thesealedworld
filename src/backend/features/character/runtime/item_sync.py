from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SYNC_NEUTRAL_DELTA = 1
OVERLOAD_PENALTY_STEP = 0.20
OVERDRIVE_TIER_RELIEF_STEP = 0.25
OVERDRIVE_BONUS_STEP = 0.0625
OVERDRIVE_BONUS_CAP = 0.35
SKILL_BASE_PENALTY_RELIEF_AT_FULL = 0.50
DURABILITY_STRESS_STEP = 0.50
DURABILITY_STRESS_EXPONENT = 1.5


@dataclass(frozen=True, slots=True)
class ItemSyncFactors:
    delta: int
    overload: int
    overdrive: int
    overload_penalty_mult: float
    overdrive_bonus_factor: float
    durability_stress_mult: float


def symbiote_tier(symbiote: Any) -> int:
    data = _dict(symbiote)
    raw = data.get("gift_rank", data.get("tier", data.get("rank", 1)))
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return 1


def item_combat_tier(item: dict[str, Any], mechanics: dict[str, Any]) -> int:
    metadata = _dict(item.get("metadata") or mechanics.get("metadata"))
    raw = metadata.get("tier") if metadata.get("tier") is not None else mechanics.get("tier")
    if raw is None:
        raw = item.get("rarity_tier", mechanics.get("rarity_tier", 0))
    try:
        return max(1, int(raw) + 1)
    except (TypeError, ValueError):
        return 1


def sync_factors(*, symbiote_rank: int, item_tier: int) -> ItemSyncFactors:
    delta = int(symbiote_rank) - int(item_tier)
    overload = max(0, -delta - SYNC_NEUTRAL_DELTA)
    overdrive = max(0, delta - SYNC_NEUTRAL_DELTA)
    return ItemSyncFactors(
        delta=delta,
        overload=overload,
        overdrive=overdrive,
        overload_penalty_mult=round(1.0 + overload * OVERLOAD_PENALTY_STEP, 4),
        overdrive_bonus_factor=round(min(OVERDRIVE_BONUS_CAP, overdrive * OVERDRIVE_BONUS_STEP), 4),
        durability_stress_mult=round(
            1.0 + overdrive**DURABILITY_STRESS_EXPONENT * DURABILITY_STRESS_STEP,
            4,
        ),
    )


def apply_penalty_sync(
    *,
    base_value: float,
    scaled_value: float,
    skill: float,
    factors: ItemSyncFactors,
) -> tuple[float, float]:
    sign = -1.0 if scaled_value < 0 else 1.0
    base_magnitude = abs(base_value)
    scaled_magnitude = abs(scaled_value)
    tier_magnitude = max(0.0, scaled_magnitude - base_magnitude)

    if factors.overload:
        tier_magnitude *= factors.overload_penalty_mult

    if factors.overdrive:
        tier_magnitude *= max(0.0, 1.0 - factors.overdrive * OVERDRIVE_TIER_RELIEF_STEP)

    remaining = base_magnitude + tier_magnitude
    skill_value = max(0.0, min(1.0, float(skill or 0.0)))
    remaining *= 1.0 - skill_value * SKILL_BASE_PENALTY_RELIEF_AT_FULL

    bonus = base_magnitude * factors.overdrive_bonus_factor
    effective = max(0.0, remaining - bonus) * sign
    return round(effective, 4), round(bonus, 4)


def _dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {}
    return {}
