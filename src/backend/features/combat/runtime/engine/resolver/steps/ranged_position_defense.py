"""Ranged-combat positional defense step for archer targets."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.combat.dto.pipeline import CombatEventDTO
from src.backend.features.combat.runtime.engine.math_core import MathCore
from src.backend.features.combat.runtime.engine.ranged_position import RangedPositionService

from ..support import armor_math, token_awarder, trace_writer, trigger_activator
from ._base import ResolverStep

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorStats
    from src.backend.features.combat.dto.pipeline import InteractionResultDTO, PipelineContextDTO


class RangedPositionDefenseStep(ResolverStep):
    __slots__ = ()

    def is_enabled(self, ctx: PipelineContextDTO) -> bool:
        return ctx.stages.check_ranged_position_defense

    def run(
        self,
        atk: ActorStats,
        def_: ActorStats,
        ctx: PipelineContextDTO,
        res: InteractionResultDTO,
    ) -> bool:
        if not ctx.stages.check_ranged_position_defense:
            return False

        position_before_trigger = RangedPositionService.normalize_position(ctx.flags.meta.target_ranged_position)
        trigger_fact_start = len(res.trigger_facts)
        trigger_activator.resolve_triggers(ctx, res, "ON_PRE_EVASION", source_stats=def_)

        if not RangedPositionService.target_defense_applies(ctx):
            trace_writer.trace_step(
                res,
                "ranged_position_defense",
                "skip",
                position=ctx.flags.meta.target_ranged_position,
                weapon_class=ctx.flags.meta.weapon_class,
                source_type=ctx.flags.meta.source_type,
            )
            return False

        if _ranged_backstep_trigger_fired(res, trigger_fact_start):
            _apply_ranged_backstep_effect(atk, def_, ctx, res, position_before_trigger)

        source_id = res.source_id if res.source_id is not None else "0"
        target_id = res.target_id if res.target_id is not None else "0"
        chance, details = RangedPositionService.ranged_avoid_chance(atk, def_, ctx)
        roll, passed = MathCore.roll_chance(chance)
        trace_writer.trace_roll(res, "ranged_position_defense", chance, roll, passed, **details)

        if passed:
            res.is_dodged = True
            token_awarder.award_defender_token(res, "dodge")
            res.events.append(CombatEventDTO(type="DODGE", source_id=source_id, target_id=target_id))
            trigger_activator.resolve_triggers(ctx, res, "ON_DODGE")
            return True

        trigger_activator.resolve_triggers(ctx, res, "ON_DODGE_FAIL")
        return False


ranged_position_defense_step = RangedPositionDefenseStep()


def _ranged_backstep_trigger_fired(res: InteractionResultDTO, start_index: int) -> bool:
    return any(fact.trigger_id == "style_ranged_perfect_backstep" for fact in res.trigger_facts[max(0, start_index) :])


def _apply_ranged_backstep_effect(
    atk: ActorStats,
    def_: ActorStats,
    ctx: PipelineContextDTO,
    res: InteractionResultDTO,
    position_before_trigger: str,
) -> None:
    position = RangedPositionService.normalize_position(position_before_trigger)
    if position == "far":
        _apply_far_ranged_punish(atk, def_, ctx, res)
        return

    improved = RangedPositionService.improve_position(position, 1)
    ctx.flags.meta.target_ranged_position = improved
    res.action_facts["ranged_current_target_position_applied"] = improved


def _apply_far_ranged_punish(
    atk: ActorStats,
    def_: ActorStats,
    ctx: PipelineContextDTO,
    res: InteractionResultDTO,
) -> None:
    if res.source_id is None or res.target_id is None:
        return

    crit_mult = 2.0
    raw_damage = max(0.0, float(def_.mods.main_hand_damage_base or 0.0)) * crit_mult
    mitigation_pct = armor_math.effective_physical_resistance(def_, atk, ctx)
    after_resist = raw_damage * max(0.0, 1.0 - mitigation_pct)
    armor = armor_math.effective_armor(def_, atk, ctx, incoming_damage=after_resist)
    punish_damage = max(0, int(after_resist - armor))

    res.is_ranged_punish = True
    res.ranged_punish_crit_mult = crit_mult
    res.ranged_punish_damage = punish_damage
    res.action_facts["ranged_far_punish_damage"] = punish_damage
    res.action_facts["ranged_far_punish_crit_mult"] = crit_mult
    res.events.append(
        CombatEventDTO(
            type="HIT",
            source_id=res.target_id,
            target_id=res.source_id,
            value=punish_damage,
            resource="hp",
            action_id="ranged_far_punish",
            tags=["RANGED_PUNISH", "CRIT"],
        )
    )
