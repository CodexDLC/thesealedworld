"""Imperative resolver orchestrator.

Drives step instances in the order defined by the original ``resolve_exchange``
flow. This is intentionally an explicit function with early-returns, not a
registry/loop — block, parry, and evasion each short-circuit damage when they
pass, and the post-damage ON_CHECK_CONTROL emission is conditional on
``res.is_hit``. Keeping the flow imperative makes those branches obvious and
makes adding new conditional stages a local edit, not a reorganization.

``damage_callable`` is passed by ``CombatResolver.resolve_exchange``. In
Phase 4 it is the ``_step_calculate_damage`` facade on ``CombatResolver``
(itself a thin wrapper around the legacy implementation that still lives in
``__init__.py``). In Phase 5 it is replaced by ``damage_step.run``.

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
)
from .support import trigger_activator

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

    if evasion_step.run(atk, def_, ctx, res):
        counter_check_step.run(atk, def_, ctx, res)
        return

    if parry_step.run(atk, def_, ctx, res):
        counter_check_step.run(atk, def_, ctx, res)
        return

    if block_step.run(atk, def_, ctx, res):
        counter_check_step.run(atk, def_, ctx, res)
        return

    damage_callable(atk, def_, ctx, res)
    healing_step.run(atk, def_, ctx, res)

    if res.is_hit:
        trigger_activator.resolve_triggers(ctx, res, "ON_CHECK_CONTROL")
