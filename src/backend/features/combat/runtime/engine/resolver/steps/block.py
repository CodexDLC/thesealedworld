"""Block step (shield block).

A successful shield block is a shield-contact event, not a full damage cancel:
it rolls a defense/counter branch (see ``armor_math.roll_shield_block_branch``),
sets ``res.shield_block_branch``, and only emits ON_BLOCK when the branch is
``counter`` (the defense branch is a passive mitigation handled in the damage
phase). Damage calculation continues regardless of block outcome — the actual
mitigation/reflect is applied inside ``steps/damage/shield_absorb.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.combat.dto.pipeline import CombatEventDTO
from src.backend.features.combat.runtime.engine.math_core import MathCore
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
            res.shield_block_branch = armor_math.roll_shield_block_branch(def_, ctx, res)
            token_awarder.award_defender_token(res, "block")
            res.events.append(CombatEventDTO(type="BLOCK", source_id=source_id, target_id=target_id))
            if res.shield_block_branch == "counter":
                trigger_activator.resolve_triggers(ctx, res, "ON_BLOCK")
            return True

        block_base = def_.mods.block
        block_cap = def_.mods.shield_block_cap
        shield_mastery = max(0.0, min(1.0, float(def_.skills.skill_shield_mastery or 0.0)))
        skill_bonus = current_tunables().shield_block_skill_bonus_at_full * shield_mastery
        block_chance = (block_base + skill_bonus) * max(0.0, ctx.mods.shield_block_chance_mult)

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
            skill=shield_mastery,
            skill_bonus=skill_bonus,
            shield_block_chance_mult=max(0.0, ctx.mods.shield_block_chance_mult),
            target_block_mult=block_mult,
        )

        if passed:
            res.is_blocked = True
            res.shield_block_branch = armor_math.roll_shield_block_branch(def_, ctx, res)
            token_awarder.award_defender_token(res, "block")
            res.events.append(CombatEventDTO(type="BLOCK", source_id=source_id, target_id=target_id))
            if res.shield_block_branch == "counter":
                trigger_activator.resolve_triggers(ctx, res, "ON_BLOCK")
            return True

        trigger_activator.resolve_triggers(ctx, res, "ON_BLOCK_FAIL")
        return False


block_step = BlockStep()
