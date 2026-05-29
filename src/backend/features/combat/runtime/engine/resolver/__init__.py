"""CombatResolver facade.

Public contract preserved: ``from ...engine.resolver import CombatResolver``
and ``CombatResolver.resolve_exchange(atk, def_, ctx)`` is the sole public
entry point. All step / helper / support logic lives in submodules
(``orchestrator``, ``steps/*``, ``support/*``); ``CombatResolver`` is a
single-method namespace kept solely to preserve the long-standing import
path used across the codebase.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.combat.dto.pipeline import InteractionResultDTO

from .orchestrator import run_exchange
from .steps.damage import damage_step

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorStats
    from src.backend.features.combat.dto.pipeline import PipelineContextDTO


class CombatResolver:
    """Stateless math engine. Computes one Attacker → Defender exchange."""

    @classmethod
    def resolve_exchange(
        cls,
        attacker_stats: ActorStats,
        defender_stats: ActorStats,
        context: PipelineContextDTO,
    ) -> InteractionResultDTO:
        result = context.result
        if result is None:
            result = InteractionResultDTO()

        if not context.phases.run_calculator:
            return result

        if result.source_id is None and context.result.source_id is not None:
            result.source_id = context.result.source_id
        if result.target_id is None and context.result.target_id is not None:
            result.target_id = context.result.target_id

        run_exchange(
            attacker_stats,
            defender_stats,
            context,
            result,
            damage_callable=damage_step.run,
        )

        return result
