"""Shield absorb / reflect for successful shield block contacts."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
