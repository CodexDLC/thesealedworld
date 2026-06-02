"""Damage step orchestrator — chains the 7 sub-phases of damage calculation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .._base import ResolverStep
from . import damage_event, elemental, final_clamp, physical, pure, ranged_position_damage, raw_roll
from ._state import DamageState

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorStats
    from src.backend.features.combat.dto.pipeline import InteractionResultDTO, PipelineContextDTO


class DamageStep(ResolverStep):
    __slots__ = ()

    def is_enabled(self, ctx: PipelineContextDTO) -> bool:
        return ctx.stages.calculate_damage

    def run(
        self,
        atk: ActorStats,
        def_: ActorStats,
        ctx: PipelineContextDTO,
        res: InteractionResultDTO,
    ) -> float:
        if not ctx.stages.calculate_damage:
            return 0.0

        state = DamageState()
        raw_roll.apply(state, atk, def_, ctx, res)
        physical.apply(state, atk, def_, ctx, res)
        pure.apply(state, atk, def_, ctx, res)
        elemental.apply(state, atk, def_, ctx, res)
        ranged_position_damage.apply(state, atk, def_, ctx, res)
        final_clamp.apply(state, atk, def_, ctx, res)
        damage_event.emit(state, atk, def_, ctx, res)

        return state.total_damage


damage_step = DamageStep()
