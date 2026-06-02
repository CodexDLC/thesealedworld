"""Ranged position post-mitigation damage multipliers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.combat.runtime.engine.ranged_position import (
    INCOMING_MELEE_DAMAGE_MULT,
    OUTGOING_DAMAGE_MULT,
    RangedPositionService,
)

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
    if RangedPositionService.archer_bow_attack_applies(ctx):
        position = RangedPositionService.normalize_position(ctx.flags.meta.source_ranged_position)
        mult = OUTGOING_DAMAGE_MULT[position]
        bonus_mult = max(0.0, float(res.action_facts.get("ranged_outgoing_damage_bonus_mult", 1.0) or 1.0))
        state.total_damage = round(state.total_damage * mult * bonus_mult, 8)
        state.ranged_position_outgoing_mult = mult
        state.ranged_position_outgoing_bonus_mult = bonus_mult
        state.ranged_position_source = position

    if RangedPositionService.target_defense_applies(ctx):
        position = RangedPositionService.normalize_position(ctx.flags.meta.target_ranged_position)
        mult = INCOMING_MELEE_DAMAGE_MULT[position]
        state.total_damage = round(state.total_damage * mult, 8)
        state.ranged_position_incoming_mult = mult
        state.ranged_position_target = position
