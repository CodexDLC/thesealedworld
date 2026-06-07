from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from src.backend.infrastructure.game_config.manager import GameConfigManager


@dataclass(frozen=True)
class CombatTunables:
    """Snapshot of combat-balance scalars consumed by CombatResolver.

    Defaults equal the historical module-level constants in resolver.py; nothing
    changes behaviorally unless a Redis-backed override is loaded via
    load_combat_tunables(...).
    """

    parry_skill_mult_per_point: float = 4.0
    base_accuracy_chance: float = 0.60
    skill_accuracy_bonus_at_full: float = 0.40
    accuracy_chance_cap: float = 0.90
    accuracy_penalty_weapon_skill_reduction_at_full: float = 0.45
    accuracy_penalty_style_skill_reduction_at_full: float = 0.45
    accuracy_penalty_min_multiplier: float = 0.10
    unarmed_min_efficiency: float = 0.5
    unarmed_max_efficiency: float = 3.0
    unarmed_novice_spread: float = 0.5
    unarmed_master_spread: float = 0.1
    token_bonus_chance: float = 0.30
    shield_block_power_to_chance: float = 0.015
    shield_block_evasion_bonus_rate: float = 1.0
    shield_block_base_cap: float = 0.45
    shield_block_mastery_cap_bonus: float = 0.30
    shield_guard_absorb_rate: float = 0.35
    shield_guard_evasion_penalty_rate: float = 0.45
    shield_guard_evasion_penalty_floor: float = 0.35
    shield_counter_cap: float = 0.50
    shield_counter_damage_ratio: float = 0.50
    shield_opening_evasion_rate: float = 1.0
    shield_opening_min_strength: float = 0.10
    shield_opening_max_strength: float = 0.30
    armor_light_coef: float = 0.014
    armor_medium_coef: float = 0.018
    armor_heavy_coef: float = 0.027
    armor_light_cap: float = 0.90
    armor_medium_cap: float = 0.90
    armor_heavy_cap: float = 0.90


DEFAULT_COMBAT_TUNABLES = CombatTunables()

_active_tunables: ContextVar[CombatTunables] = ContextVar("combat_tunables", default=DEFAULT_COMBAT_TUNABLES)


def current_tunables() -> CombatTunables:
    return _active_tunables.get()


@contextmanager
def use_tunables(tunables: CombatTunables) -> Iterator[None]:
    token = _active_tunables.set(tunables)
    try:
        yield
    finally:
        _active_tunables.reset(token)


async def load_combat_tunables(manager: GameConfigManager | None) -> CombatTunables:
    """Build a CombatTunables snapshot from a GameConfigManager. None → defaults."""
    if manager is None:
        return DEFAULT_COMBAT_TUNABLES
    d = DEFAULT_COMBAT_TUNABLES
    return CombatTunables(
        parry_skill_mult_per_point=await manager.get_float(
            "combat", "PARRY_SKILL_MULT_PER_POINT", default=d.parry_skill_mult_per_point
        ),
        base_accuracy_chance=await manager.get_float("combat", "BASE_ACCURACY_CHANCE", default=d.base_accuracy_chance),
        skill_accuracy_bonus_at_full=await manager.get_float(
            "combat",
            "SKILL_ACCURACY_BONUS_AT_FULL",
            default=d.skill_accuracy_bonus_at_full,
        ),
        accuracy_chance_cap=await manager.get_float(
            "combat",
            "ACCURACY_CHANCE_CAP",
            default=d.accuracy_chance_cap,
        ),
        accuracy_penalty_weapon_skill_reduction_at_full=await manager.get_float(
            "combat",
            "ACCURACY_PENALTY_WEAPON_SKILL_REDUCTION_AT_FULL",
            default=d.accuracy_penalty_weapon_skill_reduction_at_full,
        ),
        accuracy_penalty_style_skill_reduction_at_full=await manager.get_float(
            "combat",
            "ACCURACY_PENALTY_STYLE_SKILL_REDUCTION_AT_FULL",
            default=d.accuracy_penalty_style_skill_reduction_at_full,
        ),
        accuracy_penalty_min_multiplier=await manager.get_float(
            "combat",
            "ACCURACY_PENALTY_MIN_MULTIPLIER",
            default=d.accuracy_penalty_min_multiplier,
        ),
        unarmed_min_efficiency=await manager.get_float(
            "combat", "UNARMED_MIN_EFFICIENCY", default=d.unarmed_min_efficiency
        ),
        unarmed_max_efficiency=await manager.get_float(
            "combat", "UNARMED_MAX_EFFICIENCY", default=d.unarmed_max_efficiency
        ),
        unarmed_novice_spread=await manager.get_float(
            "combat", "UNARMED_NOVICE_SPREAD", default=d.unarmed_novice_spread
        ),
        unarmed_master_spread=await manager.get_float(
            "combat", "UNARMED_MASTER_SPREAD", default=d.unarmed_master_spread
        ),
        token_bonus_chance=await manager.get_float("combat", "TOKEN_BONUS_CHANCE", default=d.token_bonus_chance),
        shield_block_power_to_chance=await manager.get_float(
            "combat", "SHIELD_BLOCK_POWER_TO_CHANCE", default=d.shield_block_power_to_chance
        ),
        shield_block_evasion_bonus_rate=await manager.get_float(
            "combat", "SHIELD_BLOCK_EVASION_BONUS_RATE", default=d.shield_block_evasion_bonus_rate
        ),
        shield_block_base_cap=await manager.get_float(
            "combat", "SHIELD_BLOCK_BASE_CAP", default=d.shield_block_base_cap
        ),
        shield_block_mastery_cap_bonus=await manager.get_float(
            "combat", "SHIELD_BLOCK_MASTERY_CAP_BONUS", default=d.shield_block_mastery_cap_bonus
        ),
        shield_guard_absorb_rate=await manager.get_float(
            "combat", "SHIELD_GUARD_ABSORB_RATE", default=d.shield_guard_absorb_rate
        ),
        shield_guard_evasion_penalty_rate=await manager.get_float(
            "combat", "SHIELD_GUARD_EVASION_PENALTY_RATE", default=d.shield_guard_evasion_penalty_rate
        ),
        shield_guard_evasion_penalty_floor=await manager.get_float(
            "combat", "SHIELD_GUARD_EVASION_PENALTY_FLOOR", default=d.shield_guard_evasion_penalty_floor
        ),
        shield_counter_cap=await manager.get_float("combat", "SHIELD_COUNTER_CAP", default=d.shield_counter_cap),
        shield_counter_damage_ratio=await manager.get_float(
            "combat", "SHIELD_COUNTER_DAMAGE_RATIO", default=d.shield_counter_damage_ratio
        ),
        shield_opening_evasion_rate=await manager.get_float(
            "combat", "SHIELD_OPENING_EVASION_RATE", default=d.shield_opening_evasion_rate
        ),
        shield_opening_min_strength=await manager.get_float(
            "combat", "SHIELD_OPENING_MIN_STRENGTH", default=d.shield_opening_min_strength
        ),
        shield_opening_max_strength=await manager.get_float(
            "combat", "SHIELD_OPENING_MAX_STRENGTH", default=d.shield_opening_max_strength
        ),
        armor_light_coef=await manager.get_float("combat", "ARMOR_LIGHT_COEF", default=d.armor_light_coef),
        armor_medium_coef=await manager.get_float("combat", "ARMOR_MEDIUM_COEF", default=d.armor_medium_coef),
        armor_heavy_coef=await manager.get_float("combat", "ARMOR_HEAVY_COEF", default=d.armor_heavy_coef),
        armor_light_cap=await manager.get_float("combat", "ARMOR_LIGHT_CAP", default=d.armor_light_cap),
        armor_medium_cap=await manager.get_float("combat", "ARMOR_MEDIUM_CAP", default=d.armor_medium_cap),
        armor_heavy_cap=await manager.get_float("combat", "ARMOR_HEAVY_CAP", default=d.armor_heavy_cap),
    )
