"""Crit step: roll to crit or not."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.combat.runtime.engine.math_core import MathCore

from ..support import offensive_lookup, trace_writer, trigger_activator
from ._base import ResolverStep

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorStats
    from src.backend.features.combat.dto.pipeline import InteractionResultDTO, PipelineContextDTO


class CritStep(ResolverStep):
    __slots__ = ()

    def is_enabled(self, ctx: PipelineContextDTO) -> bool:
        return ctx.stages.check_crit

    def run(
        self,
        atk: ActorStats,
        def_: ActorStats,
        ctx: PipelineContextDTO,
        res: InteractionResultDTO,
    ) -> None:
        if not ctx.stages.check_crit:
            return

        if ctx.flags.force.crit:
            res.is_crit = True
            trigger_activator.apply_ammo_crit_payload(ctx, res)
            if not ctx.flags.restriction.suppress_crit_triggers:
                trigger_activator.resolve_triggers(ctx, res, "ON_CRIT")
            return

        if ctx.flags.restriction.cannot_crit:
            trigger_activator.resolve_triggers(ctx, res, "ON_CRIT_FAIL")
            return

        is_magic = False
        elements = ["fire", "water", "air", "earth", "light", "darkness", "arcane", "nature"]
        for elem in elements:
            if getattr(ctx.flags.damage, elem, False):
                is_magic = True
                break

        if is_magic:
            my_crit_chance = atk.mods.magical_crit_chance
        else:
            my_crit_chance = offensive_lookup.get_offensive_val(atk, ctx, "crit_chance")

        skill_multiplier = 1.0
        if ctx.flags.meta.weapon_class:
            skill_key = f"skill_{ctx.flags.meta.weapon_class}"
            skill_val = getattr(atk.skills, skill_key, 0.0)
            skill_multiplier = 1.0 + skill_val

        final_chance = my_crit_chance * skill_multiplier
        crit_cap = offensive_lookup.get_offensive_val(atk, ctx, "crit_cap")
        final_chance = min(final_chance, crit_cap)

        roll, passed = MathCore.roll_chance(final_chance)
        trace_writer.trace_roll(
            res,
            "crit",
            final_chance,
            roll,
            passed,
            base=my_crit_chance,
            cap=crit_cap,
            skill_mult=skill_multiplier,
        )

        if passed:
            res.is_crit = True
            trigger_activator.apply_ammo_crit_payload(ctx, res)
            if not ctx.flags.restriction.suppress_crit_triggers:
                trigger_activator.resolve_triggers(ctx, res, "ON_CRIT")
        else:
            trigger_activator.resolve_triggers(ctx, res, "ON_CRIT_FAIL")


crit_step = CritStep()
