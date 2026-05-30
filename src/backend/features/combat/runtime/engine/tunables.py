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
    shield_block_skill_bonus_at_full: float = 0.32
    shield_mastery_absorb_cap_ratio_at_full: float = 0.50
    shield_mastery_reflect_ratio_at_full: float = 1.00
    base_accuracy_chance: float = 0.70
    skill_accuracy_bonus_at_full: float = 0.30
    accuracy_chance_cap: float = 0.90
    accuracy_penalty_weapon_skill_reduction_at_full: float = 0.45
    accuracy_penalty_style_skill_reduction_at_full: float = 0.45
    accuracy_penalty_min_multiplier: float = 0.10
    unarmed_min_efficiency: float = 0.5
    unarmed_max_efficiency: float = 3.0
    unarmed_novice_spread: float = 0.5
    unarmed_master_spread: float = 0.1
    token_bonus_chance: float = 0.30


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
        shield_block_skill_bonus_at_full=await manager.get_float(
            "combat",
            "SHIELD_BLOCK_SKILL_BONUS_AT_FULL",
            default=d.shield_block_skill_bonus_at_full,
        ),
        shield_mastery_absorb_cap_ratio_at_full=await manager.get_float(
            "combat",
            "SHIELD_MASTERY_ABSORB_CAP_RATIO_AT_FULL",
            default=d.shield_mastery_absorb_cap_ratio_at_full,
        ),
        shield_mastery_reflect_ratio_at_full=await manager.get_float(
            "combat",
            "SHIELD_MASTERY_REFLECT_RATIO_AT_FULL",
            default=d.shield_mastery_reflect_ratio_at_full,
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
    )
