from __future__ import annotations

from typing import Any

MASTERY_STAT_DAMAGE_FLOOR = 0.25
SPREAD_REDUCTION_AT_FULL_MASTERY = 0.50
SHIELD_STYLE_GUARD_POWER_RATIO = 0.35

WEAPON_STAT_DAMAGE_WEIGHTS: dict[str, dict[str, float]] = {
    "swords": {"strength": 0.55, "agility": 0.45},
    "fencing": {"strength": 0.25, "agility": 0.75},
    "polearms": {"strength": 0.60, "agility": 0.40},
    "macing": {"strength": 0.75, "agility": 0.25},
    "archery": {"strength": 0.45, "agility": 0.55},
}

SHIELD_STYLE_GUARD_WEIGHTS: dict[str, float] = {
    "endurance": 0.60,
    "strength": 0.40,
}


class BasePowerAssembler:
    """Build weapon base power from item power, body stats, and mastery."""

    @classmethod
    def apply(cls, actor: Any, calculated_mods: dict[str, Any]) -> None:
        cls.apply_to_values(
            calculated_mods,
            loadout_layout=actor.loadout.layout,
            skills=actor.skills,
        )

    @classmethod
    def apply_to_values(
        cls,
        calculated_mods: dict[str, Any],
        *,
        loadout_layout: dict[str, str],
        skills: dict[str, Any],
    ) -> None:
        for slot in ("main_hand", "off_hand"):
            cls._apply_slot(calculated_mods, slot, loadout_layout=loadout_layout, skills=skills)
        cls._apply_shield_style(calculated_mods, loadout_layout=loadout_layout)

    @classmethod
    def _apply_slot(
        cls,
        calculated_mods: dict[str, Any],
        slot: str,
        *,
        loadout_layout: dict[str, str],
        skills: dict[str, Any],
    ) -> None:
        skill_key = loadout_layout.get(slot)
        if not skill_key or not skill_key.startswith("skill_"):
            return

        weapon_class = skill_key.removeprefix("skill_")
        if weapon_class == "unarmed":
            return

        weights = WEAPON_STAT_DAMAGE_WEIGHTS.get(weapon_class)
        if weights is None:
            return

        damage_key = f"{slot}_damage_base"
        weapon_power = cls._float(calculated_mods.get(damage_key))
        if weapon_power <= 0:
            return

        mastery = cls._clamp(cls._float(skills.get(skill_key)), 0.0, 1.0)
        mastery_factor = MASTERY_STAT_DAMAGE_FLOOR + ((1.0 - MASTERY_STAT_DAMAGE_FLOOR) * mastery)
        stat_raw = cls._weighted_stat_power(calculated_mods, weights)
        stat_effective = stat_raw * mastery_factor

        calculated_mods[f"{slot}_weapon_power"] = round(weapon_power, 4)
        calculated_mods[f"{slot}_stat_damage_raw"] = round(stat_raw, 4)
        calculated_mods[f"{slot}_stat_damage_effective"] = round(stat_effective, 4)
        calculated_mods[f"{slot}_mastery_factor"] = round(mastery_factor, 4)
        calculated_mods[damage_key] = round(weapon_power + stat_effective, 4)

        spread_key = f"{slot}_damage_spread"
        raw_spread = cls._float(calculated_mods.get(spread_key, 0.1))
        calculated_mods[f"{slot}_damage_spread_raw"] = round(raw_spread, 4)
        calculated_mods[spread_key] = round(
            max(0.0, raw_spread * (1.0 - (SPREAD_REDUCTION_AT_FULL_MASTERY * mastery))), 4
        )

    @classmethod
    def _apply_shield_style(cls, calculated_mods: dict[str, Any], *, loadout_layout: dict[str, str]) -> None:
        if loadout_layout.get("off_hand") != "skill_shield_mastery":
            return
        if loadout_layout.get("tactical_style") != "skill_shield_mastery":
            return

        guard_power = cls._float(calculated_mods.get("shield_guard_power"))
        if guard_power <= 0:
            return

        stat_raw = cls._weighted_stat_power(calculated_mods, SHIELD_STYLE_GUARD_WEIGHTS)
        if stat_raw <= 0:
            return

        bonus = stat_raw * SHIELD_STYLE_GUARD_POWER_RATIO
        calculated_mods["shield_style_guard_power_raw"] = round(stat_raw, 4)
        calculated_mods["shield_style_guard_power_bonus"] = round(bonus, 4)
        calculated_mods["shield_guard_power"] = round(guard_power + bonus, 4)

    @classmethod
    def _weighted_stat_power(cls, calculated_mods: dict[str, Any], weights: dict[str, float]) -> float:
        total = 0.0
        for stat_key, weight in weights.items():
            total += cls._float(calculated_mods.get(f"physical_{stat_key}_power")) * weight
        return total

    @staticmethod
    def _float(value: Any) -> float:
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))


__all__ = [
    "BasePowerAssembler",
    "MASTERY_STAT_DAMAGE_FLOOR",
    "SHIELD_STYLE_GUARD_POWER_RATIO",
    "SHIELD_STYLE_GUARD_WEIGHTS",
    "SPREAD_REDUCTION_AT_FULL_MASTERY",
    "WEAPON_STAT_DAMAGE_WEIGHTS",
]
