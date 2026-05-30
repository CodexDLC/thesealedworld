"""Mutable in-memory battle state for auto battle and training simulations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.backend.features.combat.runtime.engine.victory_checker import VictoryChecker
from src.backend.features.combat.runtime.simulation.telemetry import CombatTelemetry

if TYPE_CHECKING:
    from src.backend.features.combat.dto.ids import ActorIdLike
    from src.backend.features.combat.dto.session import BattleContext


@dataclass(frozen=True)
class InMemoryBattleLimits:
    """Runtime limits for bounded simulation runs."""

    max_rounds: int = 20
    max_actions_per_round: int = 200
    candidate_limit: int = 1
    force_unanswered_exchange: bool = True


@dataclass
class InMemoryBattleState:
    """BattleContext plus local simulation bookkeeping.

    This object deliberately has no Redis, ARQ, lock, or session-manager
    dependency. The existing executor mutates ``ctx``; this state only commits
    the executor's pending buffers back into the in-memory meta/queues.
    """

    ctx: BattleContext
    limits: InMemoryBattleLimits = field(default_factory=InMemoryBattleLimits)
    seed: int = 0
    round_index: int = 0
    telemetry: CombatTelemetry = field(default_factory=CombatTelemetry)

    def alive_actors(self):
        return [actor for actor in self.ctx.actors.values() if actor.is_alive]

    def winner(self) -> str | None:
        return VictoryChecker.check_battle_end(self.ctx.meta)

    def commit_executor_buffers(self) -> None:
        dead_actor_ids = {str(actor_id) for actor_id in self.ctx.meta.dead_actors}
        dead_actor_ids.update(str(actor_id) for actor_id in self.ctx.pending_dead_actors)
        for actor_id, actor in self.ctx.actors.items():
            if not actor.is_alive:
                dead_actor_ids.add(str(actor_id))
                actor.meta.is_dead = True

        self.ctx.meta.dead_actors = sorted(dead_actor_ids)
        self.ctx.meta.active_actors_count = sum(
            1 for actor in self.ctx.actors.values() if str(actor.meta.id) not in dead_actor_ids
        )

        self._commit_target_returns(dead_actor_ids)
        self.ctx.pending_logs.clear()
        self.ctx.pending_result_support_tasks.clear()
        self.ctx.pending_target_returns.clear()
        self.ctx.pending_dead_actors.clear()

    def _commit_target_returns(self, dead_actor_ids: set[str]) -> None:
        for pair in self.ctx.pending_target_returns:
            source_id = pair["source_id"]
            target_id = pair["target_id"]
            if str(source_id) in dead_actor_ids or str(target_id) in dead_actor_ids:
                continue
            targets = self.ctx.targets.setdefault(source_id, [])
            if not self._contains_actor_id(targets, target_id):
                targets.append(target_id)

    @staticmethod
    def _contains_actor_id(values: list[ActorIdLike], candidate: ActorIdLike) -> bool:
        return any(str(value) == str(candidate) for value in values)
