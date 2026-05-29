"""Block step (shield block)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.combat.dto.pipeline import CombatEventDTO
from src.backend.features.combat.runtime.engine.math_core import MathCore

from ..support import token_awarder, trace_writer, trigger_activator
from ._base import ResolverStep

SHIELD_BLOCK_SKILL_MULT_PER_POINT = 1.5

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorStats
    from src.backend.features.combat.dto.pipeline import InteractionResultDTO, PipelineContextDTO


class BlockStep(ResolverStep):
    __slots__ = ()

    def is_enabled(self, ctx: PipelineContextDTO) -> bool:
        return ctx.stages.check_block

    def run(
        self,
        atk: ActorStats,
        def_: ActorStats,
        ctx: PipelineContextDTO,
        res: InteractionResultDTO,
    ) -> bool:
        if not ctx.stages.check_block:
            return False

        source_id = res.source_id if res.source_id is not None else "0"
        target_id = res.target_id if res.target_id is not None else "0"

        if ctx.flags.restriction.ignore_block:
            trigger_activator.resolve_triggers(ctx, res, "ON_BLOCK_FAIL")
            return False
        if ctx.flags.force.block:
            res.is_blocked = True
            token_awarder.award_defender_token(res, "block")
            res.events.append(CombatEventDTO(type="BLOCK", source_id=source_id, target_id=target_id))
            trigger_activator.resolve_triggers(ctx, res, "ON_BLOCK")
            return True

        block_base = def_.mods.block
        block_cap = def_.mods.shield_block_cap
        parrying = def_.skills.skill_parrying
        skill_mult = 1.0 + (SHIELD_BLOCK_SKILL_MULT_PER_POINT * parrying)
        block_chance = block_base * skill_mult

        final_chance = block_chance if ctx.flags.formula.ignore_block_cap else min(block_chance, block_cap)

        roll, passed = MathCore.roll_chance(final_chance)
        trace_writer.trace_roll(
            res,
            "block",
            final_chance,
            roll,
            passed,
            base=block_base,
            cap=block_cap,
            skill=parrying,
            skill_mult=skill_mult,
        )

        if passed:
            res.is_blocked = True
            token_awarder.award_defender_token(res, "block")
            res.events.append(CombatEventDTO(type="BLOCK", source_id=source_id, target_id=target_id))
            trigger_activator.resolve_triggers(ctx, res, "ON_BLOCK")
            return True

        trigger_activator.resolve_triggers(ctx, res, "ON_BLOCK_FAIL")
        return False


block_step = BlockStep()
