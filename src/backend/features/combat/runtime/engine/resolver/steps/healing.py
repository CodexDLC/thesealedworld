"""Healing step."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.combat.dto.pipeline import CombatEventDTO
from src.backend.features.combat.runtime.engine.math_core import MathCore

from ._base import ResolverStep

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorStats
    from src.backend.features.combat.dto.pipeline import InteractionResultDTO, PipelineContextDTO


class HealingStep(ResolverStep):
    __slots__ = ()

    def is_enabled(self, ctx: PipelineContextDTO) -> bool:
        return ctx.stages.calculate_healing

    def run(
        self,
        atk: ActorStats,
        def_: ActorStats,
        ctx: PipelineContextDTO,
        res: InteractionResultDTO,
    ) -> float:
        if not ctx.stages.calculate_healing:
            return 0.0

        source_id = res.source_id if res.source_id is not None else "0"
        target_id = res.target_id if res.target_id is not None else "0"

        if ctx.override_damage:
            min_h, max_h = ctx.override_damage
        else:
            base = atk.mods.magical_damage
            min_h = base * 0.9
            max_h = base * 1.1

        raw_healing = MathCore.random_range(min_h, max_h)

        if res.is_crit:
            raw_healing *= 1.5
            res.crit_mult = 1.5

        final_healing = int(raw_healing)
        res.healing_final = final_healing

        if "hp" not in res.resource_changes:
            res.resource_changes["hp"] = {}
        res.resource_changes["hp"]["heal"] = f"+{final_healing}"

        tags = []
        if res.is_crit:
            tags.append("CRIT")
        res.events.append(
            CombatEventDTO(
                type="HEAL",
                source_id=source_id,
                target_id=target_id,
                value=final_healing,
                resource="hp",
                tags=tags,
            )
        )

        return float(final_healing)


healing_step = HealingStep()
