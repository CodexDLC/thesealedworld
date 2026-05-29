"""Counter-check step: rolled after a successful evasion/parry/block."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.combat.runtime.engine.math_core import MathCore

from ..support import token_awarder
from ._base import ResolverStep

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorStats
    from src.backend.features.combat.dto.pipeline import InteractionResultDTO, PipelineContextDTO


class CounterCheckStep(ResolverStep):
    __slots__ = ()

    def is_enabled(self, ctx: PipelineContextDTO) -> bool:
        return ctx.stages.check_counter and ctx.flags.state.check_counter

    def run(
        self,
        atk: ActorStats,
        def_: ActorStats,
        ctx: PipelineContextDTO,
        res: InteractionResultDTO,
    ) -> None:
        if not ctx.stages.check_counter or not ctx.flags.state.check_counter:
            return

        base_chance = def_.mods.counter_attack_chance
        cap = def_.mods.counter_attack_cap
        counter_chance = min(base_chance, cap)

        if res.is_dodged and ctx.flags.mastery.light_armor and MathCore.check_chance(0.50):
            skill_lvl = def_.skills.skill_light_armor
            mult = 1.0 + skill_lvl
            counter_chance *= mult

        if ctx.flags.formula.counter_chance_boost:
            counter_chance += 0.20

        if res.is_dodged:
            counter_chance += ctx.mods.counter_chance_bonus_on_dodge

        if res.is_parried:
            counter_chance += ctx.mods.counter_chance_bonus_on_parry

        if res.is_dodged and ctx.flags.state.counter_to_cap_on_dodge:
            counter_chance = max(counter_chance, cap)

        if (res.is_dodged and ctx.flags.state.force_counter_on_dodge) or (
            res.is_parried and ctx.flags.state.force_counter_on_parry
        ):
            counter_chance = 1.0

        if counter_chance > 0 and MathCore.check_chance(counter_chance):
            res.is_counter = True
            token_awarder.award_defender_token(res, "counter")
            res.chain_events.trigger_counter_attack = True


counter_check_step = CounterCheckStep()
