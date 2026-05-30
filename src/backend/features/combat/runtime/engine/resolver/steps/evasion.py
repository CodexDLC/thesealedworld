"""Evasion (dodge) step."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.combat.dto.pipeline import CombatEventDTO
from src.backend.features.combat.runtime.engine.math_core import MathCore

from ..support import token_awarder, trace_writer, trigger_activator
from ._base import ResolverStep

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorStats
    from src.backend.features.combat.dto.pipeline import InteractionResultDTO, PipelineContextDTO


class EvasionStep(ResolverStep):
    __slots__ = ()

    def is_enabled(self, ctx: PipelineContextDTO) -> bool:
        return ctx.stages.check_evasion

    def run(
        self,
        atk: ActorStats,
        def_: ActorStats,
        ctx: PipelineContextDTO,
        res: InteractionResultDTO,
    ) -> bool:
        if not ctx.stages.check_evasion:
            return False

        source_id = res.source_id if res.source_id is not None else "0"
        target_id = res.target_id if res.target_id is not None else "0"

        trigger_activator.resolve_triggers(ctx, res, "ON_PRE_EVASION", source_stats=def_)

        if ctx.flags.force.dodge:
            res.is_dodged = True
            token_awarder.award_defender_token(res, "dodge")
            res.events.append(CombatEventDTO(type="DODGE", source_id=source_id, target_id=target_id))
            trigger_activator.resolve_triggers(ctx, res, "ON_DODGE")
            ctx.flags.state.check_counter = True
            return True

        if ctx.flags.force.hit_evasion:
            trigger_activator.resolve_triggers(ctx, res, "ON_DODGE_FAIL")
            return False

        base_evasion = def_.mods.evasion
        evasion_cap = def_.mods.dodge_cap
        anti_evasion = atk.mods.anti_dodge_chance

        final_chance = base_evasion if ctx.flags.formula.zero_anti_evasion else base_evasion - anti_evasion
        final_chance = min(final_chance, evasion_cap)

        evasion_mult = max(0.0, ctx.mods.target_evasion_mult)
        final_chance = max(0.0, min(1.0, final_chance * evasion_mult))

        if final_chance <= 0:
            trigger_activator.resolve_triggers(ctx, res, "ON_DODGE_FAIL")
            trace_writer.trace_roll(
                res,
                "evasion",
                final_chance,
                None,
                False,
                base=base_evasion,
                cap=evasion_cap,
                anti=anti_evasion,
                target_evasion_mult=evasion_mult,
            )
            return False

        roll, passed = MathCore.roll_chance(final_chance)
        trace_writer.trace_roll(
            res,
            "evasion",
            final_chance,
            roll,
            passed,
            base=base_evasion,
            cap=evasion_cap,
            anti=anti_evasion,
            target_evasion_mult=evasion_mult,
        )

        if passed:
            res.is_dodged = True
            token_awarder.award_defender_token(res, "dodge")
            res.events.append(CombatEventDTO(type="DODGE", source_id=source_id, target_id=target_id))
            trigger_activator.resolve_triggers(ctx, res, "ON_DODGE")
            ctx.flags.state.check_counter = True
            return True

        trigger_activator.resolve_triggers(ctx, res, "ON_DODGE_FAIL")
        return False


evasion_step = EvasionStep()
