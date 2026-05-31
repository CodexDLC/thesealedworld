"""Physical damage channel: crit multiplier + resistance + armor."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...support import armor_math, token_awarder

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
    if res.is_crit:
        state.crit_multiplier = armor_math.calculate_crit_multiplier(ctx)
        res.crit_mult = state.crit_multiplier

    if not ctx.flags.damage.physical:
        return

    phys_dmg = state.raw_damage

    if res.is_crit:
        phys_dmg *= state.crit_multiplier

    state.mitigation_pct = armor_math.effective_physical_resistance(atk, def_, ctx)
    phys_dmg *= 1.0 - state.mitigation_pct
    state.after_resist = phys_dmg

    state.armor_flat, state.armor_trace = armor_math.effective_armor_trace(atk, def_, ctx)
    phys_dmg = max(0.0, phys_dmg - state.armor_flat)
    state.after_armor = phys_dmg
    state.damage_parts["physical"] = phys_dmg

    if res.is_crit:
        token_awarder.award_attacker_token(res, "crit")
    else:
        token_awarder.award_attacker_token(res, "hit")

    state.total_damage += phys_dmg
