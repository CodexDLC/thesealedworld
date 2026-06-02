"""Block step (shield block).

A successful shield block is a shield-contact event, not a full damage cancel.
The step rolls block chance from shield power plus uncapped evasion, emits the
block trigger, and may open an instant shield-counter. Damage calculation
continues; temporary shield guard power is folded into the physical armor stage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.combat.dto.pipeline import CombatEventDTO
from src.backend.features.combat.runtime.engine.math_core import MathCore
from src.backend.features.combat.runtime.engine.ranged_position import RangedPositionService
from src.backend.features.combat.runtime.engine.tunables import current_tunables

from ..support import armor_math, token_awarder, trace_writer, trigger_activator
from ._base import ResolverStep

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
            res.shield_block_branch = "defense"
            token_awarder.award_defender_token(res, "block")
            res.events.append(CombatEventDTO(type="BLOCK", source_id=source_id, target_id=target_id))
            trigger_activator.resolve_triggers(ctx, res, "ON_BLOCK")
            _try_shield_counter(atk, def_, ctx, res)
            return True

        tunables = current_tunables()
        shield_power = max(0.0, float(def_.mods.shield_guard_power or 0.0))
        evasion = max(0.0, float(def_.mods.evasion or 0.0))
        shield_mastery = max(0.0, min(1.0, float(def_.skills.skill_shield_mastery or 0.0)))
        mastery_gate = _shield_mastery_gate(shield_mastery)
        block_base = shield_power * tunables.shield_block_power_to_chance
        evasion_bonus = 1.0 + (evasion * tunables.shield_block_evasion_bonus_rate)
        block_chance = block_base * evasion_bonus * mastery_gate * max(0.0, ctx.mods.shield_block_chance_mult)

        block_cap = tunables.shield_block_base_cap + (tunables.shield_block_mastery_cap_bonus * shield_mastery)
        final_chance = block_chance if ctx.flags.formula.ignore_block_cap else min(block_chance, block_cap)
        block_mult = max(0.0, ctx.mods.target_block_mult)
        final_chance = max(0.0, min(1.0, final_chance * block_mult))

        roll, passed = MathCore.roll_chance(final_chance)
        trace_writer.trace_roll(
            res,
            "block",
            final_chance,
            roll,
            passed,
            base=block_base,
            cap=block_cap,
            evasion=evasion,
            evasion_bonus=evasion_bonus,
            shield_power=shield_power,
            shield_mastery=shield_mastery,
            mastery_gate=mastery_gate,
            shield_block_chance_mult=max(0.0, ctx.mods.shield_block_chance_mult),
            target_block_mult=block_mult,
        )

        if passed:
            res.is_blocked = True
            res.shield_block_branch = "defense"
            token_awarder.award_defender_token(res, "block")
            res.events.append(CombatEventDTO(type="BLOCK", source_id=source_id, target_id=target_id))
            trigger_activator.resolve_triggers(ctx, res, "ON_BLOCK")
            _try_shield_counter(atk, def_, ctx, res)
            return True

        trigger_activator.resolve_triggers(ctx, res, "ON_BLOCK_FAIL")
        return False


block_step = BlockStep()


def _shield_mastery_gate(shield_mastery: float) -> float:
    return 0.35 + (0.65 * max(0.0, min(1.0, shield_mastery)))


def _try_shield_counter(
    atk: ActorStats,
    def_: ActorStats,
    ctx: PipelineContextDTO,
    res: InteractionResultDTO,
) -> None:
    if res.source_id is None or res.target_id is None:
        return
    if ctx.flags.restriction.disable_passive_counter:
        return
    if not RangedPositionService.source_counter_reachable(ctx):
        return

    tunables = current_tunables()
    shield_mastery = max(0.0, min(1.0, float(def_.skills.skill_shield_mastery or 0.0)))
    mastery_gate = _shield_mastery_gate(shield_mastery)
    counter_base = max(0.0, float(def_.mods.counter_attack_chance or 0.0))
    counter_chance = min(counter_base * mastery_gate, tunables.shield_counter_cap)
    res.shield_counter_chance = counter_chance
    if counter_chance <= 0.0 or not MathCore.check_chance(counter_chance):
        return

    raw_damage = max(0.0, float(def_.mods.main_hand_damage_base or 0.0))
    raw_damage *= tunables.shield_counter_damage_ratio * mastery_gate
    mitigation_pct = armor_math.effective_physical_resistance(def_, atk, ctx)
    after_resist = raw_damage * max(0.0, 1.0 - mitigation_pct)
    armor = armor_math.effective_armor(def_, atk, ctx, incoming_damage=after_resist)
    counter_damage = max(0, int(after_resist - armor))

    res.is_shield_counter = True
    res.shield_counter_damage = counter_damage
    res.events.append(
        CombatEventDTO(
            type="HIT",
            source_id=res.target_id,
            target_id=res.source_id,
            value=counter_damage,
            resource="hp",
            action_id="shield_counter",
            tags=["SHIELD_COUNTER"],
        )
    )

    opening_strength = _shield_opening_strength(def_, shield_mastery, mastery_gate)
    res.shield_opening_strength = opening_strength
    opening_mult = max(0.0, 1.0 - opening_strength)
    res.applied_effects.append(
        {
            "id": "shield_opening",
            "target_id": res.source_id,
            "source_id": res.target_id,
            "params": {
                "evasion_mult": opening_mult,
                "parry_mult": opening_mult,
                "opening_strength": opening_strength,
            },
        }
    )


def _shield_opening_strength(def_: ActorStats, shield_mastery: float, mastery_gate: float) -> float:
    tunables = current_tunables()
    evasion = max(0.0, float(def_.mods.evasion or 0.0))
    evasion_factor = max(0.0, min(1.0, evasion * tunables.shield_opening_evasion_rate))
    opening = tunables.shield_opening_max_strength - (
        (tunables.shield_opening_max_strength - tunables.shield_opening_min_strength) * evasion_factor
    )
    if shield_mastery <= 0.0:
        return 0.0
    return max(0.0, min(1.0, opening * mastery_gate))
