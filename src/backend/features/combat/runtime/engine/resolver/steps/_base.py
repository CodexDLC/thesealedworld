"""Base protocol for resolver steps.

Each step is a stateless singleton. ``__slots__ = ()`` blocks accidental
attribute assignment which would corrupt the shared instance.

Step return contract is intentionally minimal — no ``StepOutcome`` enum —
return values match the original ``CombatResolver._step_*`` signatures so
external tests (which call the step methods directly) keep working:

- accuracy/evasion/parry/block: ``bool`` (True = passed/early-return).
- crit/counter_check: ``None``.
- damage: ``float`` (total damage).
- healing: ``float`` (final healing).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorStats
    from src.backend.features.combat.dto.pipeline import InteractionResultDTO, PipelineContextDTO


class ResolverStep:
    __slots__ = ()

    def is_enabled(self, ctx: PipelineContextDTO) -> bool:  # pragma: no cover - overridden
        raise NotImplementedError

    def run(
        self,
        atk: ActorStats,
        def_: ActorStats,
        ctx: PipelineContextDTO,
        res: InteractionResultDTO,
    ):  # pragma: no cover - overridden
        raise NotImplementedError
