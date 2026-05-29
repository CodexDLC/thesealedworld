"""Shield absorb / reflect (active when ``ctx.flags.state.partial_absorb_reflect``)."""

from __future__ import annotations

from typing import TYPE_CHECKING

SHIELD_MASTERY_ABSORB_CAP_RATIO_AT_FULL = 0.50
SHIELD_MASTERY_REFLECT_RATIO_AT_FULL = 0.50

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
    if not ctx.flags.state.partial_absorb_reflect:
        return

    state.shield_mastery = min(1.0, max(0.0, def_.skills.skill_shield_mastery))
    shield_guard_power_base = max(0.0, getattr(def_.mods, "shield_guard_power", 0.0))
    state.shield_guard_power = shield_guard_power_base * state.shield_mastery
    shield_absorb_cap_ratio = SHIELD_MASTERY_ABSORB_CAP_RATIO_AT_FULL * state.shield_mastery
    state.shield_absorb_cap = state.total_damage * shield_absorb_cap_ratio
    state.shield_absorb_ratio = shield_absorb_cap_ratio
    state.shield_reflect_ratio = (
        min(
            max(0.0, getattr(def_.mods, "shield_reflect_ratio", SHIELD_MASTERY_REFLECT_RATIO_AT_FULL)),
            SHIELD_MASTERY_REFLECT_RATIO_AT_FULL,
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
