"""Parry step."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.combat.dto.pipeline import CombatEventDTO
from src.backend.features.combat.runtime.engine.math_core import MathCore
from src.backend.features.combat.runtime.engine.tunables import current_tunables

from ..support import token_awarder, trace_writer, trigger_activator
from ._base import ResolverStep

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorStats
    from src.backend.features.combat.dto.pipeline import InteractionResultDTO, PipelineContextDTO


class ParryStep(ResolverStep):
    __slots__ = ()

    def is_enabled(self, ctx: PipelineContextDTO) -> bool:
        return ctx.stages.check_parry

    def run(
        self,
        atk: ActorStats,
        def_: ActorStats,
        ctx: PipelineContextDTO,
        res: InteractionResultDTO,
    ) -> bool:
        if not ctx.stages.check_parry:
            return False

        source_id = res.source_id if res.source_id is not None else "0"
        target_id = res.target_id if res.target_id is not None else "0"

        if ctx.flags.restriction.ignore_parry:
            trigger_activator.resolve_triggers(ctx, res, "ON_PARRY_FAIL")
            return False

        if ctx.flags.force.parry:
            res.is_parried = True
            token_awarder.award_defender_token(res, "parry")
            res.events.append(CombatEventDTO(type="PARRY", source_id=source_id, target_id=target_id))
            trigger_activator.resolve_triggers(ctx, res, "ON_PARRY")
            if ctx.flags.state.allow_counter_on_parry or ctx.flags.state.force_counter_on_parry:
                ctx.flags.state.check_counter = True
            elif ctx.flags.mastery.medium_armor and not ctx.flags.restriction.disable_passive_counter:
                mastery_chance = def_.skills.skill_medium_armor
                if MathCore.check_chance(mastery_chance):
                    ctx.flags.state.check_counter = True
            return True

        parry_base = def_.mods.parry
        parry_cap = def_.mods.parry_cap
        parrying = def_.skills.skill_parrying
        skill_mult = 1.0 + (current_tunables().parry_skill_mult_per_point * parrying)
        parry_chance = parry_base * skill_mult

        if ctx.flags.formula.ignore_parry_cap:
            final_chance = parry_chance
        else:
            final_chance = parry_chance
            final_chance = min(final_chance, parry_cap)

        parry_mult = max(0.0, ctx.mods.target_parry_mult)
        final_chance = max(0.0, min(1.0, final_chance * parry_mult))

        roll, passed = MathCore.roll_chance(final_chance)
        trace_writer.trace_roll(
            res,
            "parry",
            final_chance,
            roll,
            passed,
            base=parry_base,
            cap=parry_cap,
            skill=parrying,
            skill_mult=skill_mult,
            target_parry_mult=parry_mult,
        )

        if passed:
            res.is_parried = True
            token_awarder.award_defender_token(res, "parry")
            res.events.append(CombatEventDTO(type="PARRY", source_id=source_id, target_id=target_id))
            trigger_activator.resolve_triggers(ctx, res, "ON_PARRY")

            if ctx.flags.mastery.medium_armor and not ctx.flags.restriction.disable_passive_counter:
                mastery_chance = def_.skills.skill_medium_armor
                if MathCore.check_chance(mastery_chance):
                    ctx.flags.state.check_counter = True
            elif ctx.flags.state.allow_counter_on_parry or ctx.flags.state.force_counter_on_parry:
                ctx.flags.state.check_counter = True
            return True

        trigger_activator.resolve_triggers(ctx, res, "ON_PARRY_FAIL")
        return False


parry_step = ParryStep()
