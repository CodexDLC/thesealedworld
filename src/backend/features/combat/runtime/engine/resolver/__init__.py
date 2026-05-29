"""CombatResolver facade.

Public contract preserved: ``from ...engine.resolver import CombatResolver``
and ``CombatResolver.resolve_exchange(atk, def_, ctx)``. Internally the work
flows through the orchestrator and Step singletons; the private ``_step_*``
and helper methods remain on the class as deprecated delegates so the
existing direct-call tests in ``test_runtime_processors.py`` keep passing
until Phase 6 migrates them. All delegates carry a ``DEPRECATED facade``
comment and will be removed in Phase 6.

Damage decomposition (Phase 5) replaces the in-place ``_step_calculate_damage``
implementation below with a sub-pipeline under ``steps/damage/``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.combat.dto.pipeline import InteractionResultDTO

from .orchestrator import run_exchange
from .steps import (
    accuracy_step,
    block_step,
    counter_check_step,
    crit_step,
    evasion_step,
    healing_step,
    parry_step,
)
from .steps.damage import damage_step
from .support import (
    armor_math,
    offensive_lookup,
    token_awarder,
    trace_writer,
    trigger_activator,
)

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorStats
    from src.backend.features.combat.dto.pipeline import (
        CombatTriggerActivationDTO,
        PipelineContextDTO,
    )


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
            damage_callable=cls._step_calculate_damage,
        )

        return result

    # ----- Step facades (DEPRECATED — removed in Phase 6). -----

    @staticmethod
    def _step_accuracy_roll(atk_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO) -> bool:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return accuracy_step.run(atk_stats, atk_stats, ctx, res)

    @staticmethod
    def _step_crit_roll(
        atk_stats: ActorStats, _def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO
    ) -> None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        crit_step.run(atk_stats, _def_stats, ctx, res)

    @staticmethod
    def _step_evasion_roll(
        atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO
    ) -> bool:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return evasion_step.run(atk_stats, def_stats, ctx, res)

    @staticmethod
    def _step_parry_roll(
        atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO
    ) -> bool:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return parry_step.run(atk_stats, def_stats, ctx, res)

    @staticmethod
    def _step_block_roll(
        atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO
    ) -> bool:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return block_step.run(atk_stats, def_stats, ctx, res)

    @staticmethod
    def _step_counter_check(def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO) -> None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        counter_check_step.run(def_stats, def_stats, ctx, res)

    @staticmethod
    def _step_calculate_healing(atk_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO) -> float:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return healing_step.run(atk_stats, atk_stats, ctx, res)

    # ----- Damage step (decomposed into steps/damage/* sub-phases in Phase 5). -----

    @staticmethod
    def _step_calculate_damage(
        atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO
    ) -> float:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return damage_step.run(atk_stats, def_stats, ctx, res)

    # ----- Helper facades (DEPRECATED — removed in Phase 6). -----

    @staticmethod
    def _get_offensive_val(stats: ActorStats, ctx: PipelineContextDTO, key: str) -> float:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return offensive_lookup.get_offensive_val(stats, ctx, key)

    @staticmethod
    def _accuracy_skill_bonus(atk_stats: ActorStats, ctx: PipelineContextDTO) -> float:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return offensive_lookup.accuracy_skill_bonus(atk_stats, ctx)

    @staticmethod
    def _calculate_crit_multiplier(ctx: PipelineContextDTO) -> float:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return armor_math.calculate_crit_multiplier(ctx)

    @staticmethod
    def _effective_armor(atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO) -> float:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return armor_math.effective_armor(atk_stats, def_stats, ctx)

    @staticmethod
    def _effective_armor_trace(
        atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO
    ) -> tuple[float, dict[str, Any]]:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return armor_math.effective_armor_trace(atk_stats, def_stats, ctx)

    @staticmethod
    def _effective_physical_resistance(atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO) -> float:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return armor_math.effective_physical_resistance(atk_stats, def_stats, ctx)

    @staticmethod
    def _resolve_triggers(
        ctx: PipelineContextDTO,
        res: InteractionResultDTO,
        step_key: str,
        *,
        source_stats: ActorStats | None = None,
    ) -> None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        trigger_activator.resolve_triggers(ctx, res, step_key, source_stats=source_stats)

    @staticmethod
    def _select_trigger_activation(
        ctx: PipelineContextDTO, rule_id: str, rule_data: dict[str, Any]
    ) -> CombatTriggerActivationDTO | None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return trigger_activator.select_trigger_activation(ctx, rule_id, rule_data)

    @staticmethod
    def _trigger_chance(rule_data: dict[str, Any], *, source_stats: ActorStats | None = None) -> float:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return trigger_activator.trigger_chance(rule_data, source_stats=source_stats)

    @staticmethod
    def _apply_trigger_effects(
        ctx: PipelineContextDTO,
        res: InteractionResultDTO,
        activation: CombatTriggerActivationDTO,
        rule_id: str,
        rule_data: dict[str, Any],
        *,
        step_key: str,
    ) -> None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        trigger_activator.apply_trigger_effects(ctx, res, activation, rule_id, rule_data, step_key=step_key)

    @staticmethod
    def _apply_trigger_token_grants(res: InteractionResultDTO, rule_data: dict[str, Any]) -> None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        trigger_activator.apply_trigger_token_grants(res, rule_data)

    @staticmethod
    def _award_attacker_token(res: InteractionResultDTO, token: str) -> None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        token_awarder.award_attacker_token(res, token)

    @staticmethod
    def _award_defender_token(res: InteractionResultDTO, token: str) -> None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        token_awarder.award_defender_token(res, token)

    @staticmethod
    def _award_token(bucket: dict[str, int], token: str) -> None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        token_awarder.award_token(bucket, token)

    @staticmethod
    def _bonus_token_roll() -> bool:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return token_awarder.bonus_token_roll()

    @staticmethod
    def _trace_roll(
        res: InteractionResultDTO,
        stage: str,
        chance: float,
        roll: float | None,
        passed: bool,
        **details: Any,
    ) -> None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        trace_writer.trace_roll(res, stage, chance, roll, passed, **details)

    @staticmethod
    def _trace_step(res: InteractionResultDTO, stage: str, outcome: str, **details: Any) -> None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        trace_writer.trace_step(res, stage, outcome, **details)

    @staticmethod
    def _trace_damage(res: InteractionResultDTO, **details: Any) -> None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        trace_writer.trace_damage(res, **details)

    @staticmethod
    def _compact_details(details: dict[str, Any]) -> str:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return trace_writer.compact_details(details)

    @staticmethod
    def _compact_trace_details(details: dict[str, Any]) -> dict[str, Any]:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return trace_writer.compact_trace_details(details)
