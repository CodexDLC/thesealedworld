"""Accuracy step: roll to hit or miss."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.combat.dto.pipeline import CombatEventDTO
from src.backend.features.combat.runtime.engine.math_core import MathCore

from ..support import offensive_lookup, token_awarder, trace_writer, trigger_activator
from ..support.offensive_lookup import BASE_ACCURACY_CHANCE
from ._base import ResolverStep

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorStats
    from src.backend.features.combat.dto.pipeline import InteractionResultDTO, PipelineContextDTO


class AccuracyStep(ResolverStep):
    __slots__ = ()

    def is_enabled(self, ctx: PipelineContextDTO) -> bool:
        return ctx.stages.check_accuracy

    def run(
        self,
        atk: ActorStats,
        def_: ActorStats,
        ctx: PipelineContextDTO,
        res: InteractionResultDTO,
    ) -> bool:
        if not ctx.stages.check_accuracy:
            return True

        source_id = res.source_id if res.source_id is not None else "0"
        target_id = res.target_id if res.target_id is not None else "0"

        if ctx.flags.force.miss:
            res.is_miss = True
            token_awarder.award_defender_token(res, "tempo")
            res.events.append(CombatEventDTO(type="MISS", source_id=source_id, target_id=target_id))
            trace_writer.trace_step(res, "accuracy", "fail", reason="force_miss")
            return False

        if ctx.flags.force.hit:
            trigger_activator.resolve_triggers(ctx, res, "ON_ACCURACY_CHECK", source_stats=atk)
            trace_writer.trace_step(res, "accuracy", "pass", reason="force_hit")
            return True

        accuracy_modifier = offensive_lookup.get_offensive_val(atk, ctx, "accuracy")
        skill_bonus = offensive_lookup.accuracy_skill_bonus(atk, ctx)
        multiplier = ctx.mods.accuracy_mult
        final_acc = max(0.0, min(1.0, (BASE_ACCURACY_CHANCE + skill_bonus + accuracy_modifier) * multiplier))
        roll, passed = MathCore.roll_chance(final_acc)
        trace_writer.trace_roll(
            res,
            "accuracy",
            final_acc,
            roll,
            passed,
            base=BASE_ACCURACY_CHANCE,
            skill_bonus=skill_bonus,
            modifier=accuracy_modifier,
            mult=multiplier,
            source_type=ctx.flags.meta.source_type,
        )

        if not passed:
            res.is_miss = True
            token_awarder.award_defender_token(res, "tempo")
            res.events.append(CombatEventDTO(type="MISS", source_id=source_id, target_id=target_id))
            trigger_activator.resolve_triggers(ctx, res, "ON_MISS")
            return False

        trigger_activator.resolve_triggers(ctx, res, "ON_ACCURACY_CHECK", source_stats=atk)
        return True


accuracy_step = AccuracyStep()
