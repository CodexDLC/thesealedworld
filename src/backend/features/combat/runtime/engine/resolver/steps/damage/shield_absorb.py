"""Shield absorb / reflect.

Two paths:
1. Active block (``res.is_blocked``): branched by ``res.shield_block_branch``
   (``defense`` → absorb up to shield_guard_power; ``counter`` → reflect via
   shield_guard_power × mastery-scaled ratio). Triggered by the block step.
2. Passive partial absorb (``ctx.flags.state.partial_absorb_reflect``):
   the older mastery-driven absorb/reflect formula, kept for compatibility.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.combat.runtime.engine.tunables import current_tunables

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorStats
    from src.backend.features.combat.dto.pipeline import InteractionResultDTO, PipelineContextDTO

    from ._state import DamageState


def apply(
    state: DamageState,
    atk: ActorStats,
    def_: ActorStats,
    ctx: PipelineContextDTO,
    res: InteractionResultDTO,
) -> None:
    if res.is_blocked:
        state.shield_mastery = min(1.0, max(0.0, def_.skills.skill_shield_mastery))
        shield_guard_power_base = max(0.0, getattr(def_.mods, "shield_guard_power", 0.0))
        state.shield_guard_power = shield_guard_power_base * (1.0 + (0.50 * state.shield_mastery))
        state.shield_guard_power *= max(0.0, ctx.mods.shield_guard_power_mult)
        branch = res.shield_block_branch
        if branch == "defense":
            state.shield_absorb_ratio = 1.0
            state.shield_absorb_cap = state.total_damage
            state.shield_absorb = min(state.total_damage, state.shield_guard_power)
            state.total_damage -= state.shield_absorb
        elif branch == "counter":
            state.shield_reflect_ratio = 1.0 + (0.50 * state.shield_mastery)
            state.shield_reflect_ratio *= max(0.0, ctx.mods.shield_counter_power_mult)
            state.shield_reflect_base = (
                min(state.total_damage, state.shield_guard_power)
                if ctx.flags.formula.shield_counter_from_absorbed
                else shield_guard_power_base
            )
            state.shield_reflect = state.shield_reflect_base * state.shield_reflect_ratio
            res.reflected_damage += int(state.shield_reflect)
        return

    if not ctx.flags.state.partial_absorb_reflect:
        return

    tunables = current_tunables()
    state.shield_mastery = min(1.0, max(0.0, def_.skills.skill_shield_mastery))
    shield_guard_power_base = max(0.0, getattr(def_.mods, "shield_guard_power", 0.0))
    state.shield_guard_power = shield_guard_power_base * state.shield_mastery
    shield_absorb_cap_ratio = tunables.shield_mastery_absorb_cap_ratio_at_full * state.shield_mastery
    state.shield_absorb_cap = state.total_damage * shield_absorb_cap_ratio
    state.shield_absorb_ratio = shield_absorb_cap_ratio
    state.shield_reflect_ratio = (
        min(
            max(
                0.0,
                getattr(
                    def_.mods,
                    "shield_reflect_ratio",
                    tunables.shield_mastery_reflect_ratio_at_full,
                ),
            ),
            tunables.shield_mastery_reflect_ratio_at_full,
        )
        * state.shield_mastery
    )

    raw_shield_absorb = (state.total_damage * max(0.0, getattr(def_.mods, "shield_absorb_ratio", 0.40))) + (
        state.shield_guard_power
    )
    state.shield_absorb = min(state.total_damage, state.shield_absorb_cap, raw_shield_absorb)
    state.total_damage -= state.shield_absorb
    state.shield_reflect = state.shield_absorb * state.shield_reflect_ratio
    res.reflected_damage += int(state.shield_reflect)
