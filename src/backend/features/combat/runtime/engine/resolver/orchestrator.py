"""Imperative resolver orchestrator.

Drives step instances in the order defined by the original ``resolve_exchange``
flow. This is intentionally an explicit function with early-returns, not a
registry/loop. Evasion and parry short-circuit damage when they pass; block
does **not** short-circuit — a successful shield block is a contact event
(branch defense/counter) handled inside the damage sub-pipeline. The
post-damage ON_CHECK_CONTROL emission is conditional on ``res.is_hit``.

This module imports neither ``CombatResolver`` nor anything from the parent
package's ``__init__.py`` — that breaks the otherwise-circular import.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from .steps import (
    accuracy_step,
    block_step,
    counter_check_step,
    crit_step,
    evasion_step,
    healing_step,
    parry_step,
    ranged_position_defense_step,
)
from .support import token_awarder, trigger_activator

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorStats
    from src.backend.features.combat.dto.pipeline import InteractionResultDTO, PipelineContextDTO

    DamageCallable = Callable[[ActorStats, ActorStats, PipelineContextDTO, InteractionResultDTO], float]


def run_exchange(
    atk: ActorStats,
    def_: ActorStats,
    ctx: PipelineContextDTO,
    res: InteractionResultDTO,
    *,
    damage_callable: DamageCallable,
) -> None:
    """Execute the resolver pipeline. Mutates ``res`` in place."""
    if not accuracy_step.run(atk, def_, ctx, res):
        return

    crit_step.run(atk, def_, ctx, res)
    _mark_accuracy_success(res)

    if evasion_step.run(atk, def_, ctx, res):
        counter_check_step.run(atk, def_, ctx, res)
        return

    if parry_step.run(atk, def_, ctx, res):
        counter_check_step.run(atk, def_, ctx, res)
        return

    # Block does NOT early-return — successful block is a contact event
    # (defense / counter branch) folded into damage / shield-absorb math.
    if block_step.run(atk, def_, ctx, res):
        counter_check_step.run(atk, def_, ctx, res)

    if ranged_position_defense_step.run(atk, def_, ctx, res):
        return

    damage_callable(atk, def_, ctx, res)
    healing_step.run(atk, def_, ctx, res)

    if res.is_hit:
        trigger_activator.resolve_triggers(ctx, res, "ON_CHECK_CONTROL")


def _mark_accuracy_success(res: InteractionResultDTO) -> None:
    """Record offensive mastery success before defensive reactions resolve."""
    res.is_hit = True
    if res.is_crit:
        token_awarder.award_attacker_token(res, "crit")
    else:
        token_awarder.award_attacker_token(res, "hit")
