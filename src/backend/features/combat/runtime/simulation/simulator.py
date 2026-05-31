"""In-memory combat simulator built around the real combat executor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.backend.features.combat.runtime.processors.executor import CombatExecutor
from src.backend.features.combat.runtime.simulation.action_collector import SimulationActionCollector
from src.backend.features.combat.runtime.simulation.intent_provider import AiSimulationIntentProvider

if TYPE_CHECKING:
    from src.backend.features.combat.dto.action import CombatMoveDTO
    from src.backend.features.combat.runtime.simulation.intent_provider import SimulationIntentProvider
    from src.backend.features.combat.runtime.simulation.state import InMemoryBattleState
    from src.backend.features.combat.runtime.simulation.telemetry import CombatTelemetry


@dataclass(frozen=True)
class SimulationStepResult:
    processed_move_ids: list[str]
    action_count: int
    winner: str | None


@dataclass(frozen=True)
class SimulationRunResult:
    winner: str
    rounds_completed: int
    telemetry: CombatTelemetry
    final_hp_by_actor: dict[str, int]
    completion_reason: str = "victory"
    final_tick_index: int = 0


class InMemoryCombatSimulator:
    """Run bounded combat loops without Redis or ARQ."""

    def __init__(
        self,
        *,
        executor: CombatExecutor | None = None,
        intent_provider: SimulationIntentProvider | None = None,
        action_collector: SimulationActionCollector | None = None,
    ) -> None:
        self.executor = executor or CombatExecutor()
        self.intent_provider = intent_provider or AiSimulationIntentProvider()
        self.action_collector = action_collector or SimulationActionCollector()

    async def run(self, state: InMemoryBattleState) -> SimulationRunResult:
        winner = state.winner()
        while winner is None and state.round_index < state.limits.max_rounds:
            step = await self.step(state)
            winner = step.winner
            if step.action_count == 0:
                break

        completion_reason = "victory"
        if winner is None:
            winner = "draw"
            completion_reason = "max_rounds_reached" if state.round_index >= state.limits.max_rounds else "no_actions"
        state.ctx.meta.winner = winner
        state.ctx.meta.active = 0
        return SimulationRunResult(
            winner=winner,
            rounds_completed=state.round_index,
            telemetry=state.telemetry,
            final_hp_by_actor={str(actor_id): actor.meta.hp for actor_id, actor in state.ctx.actors.items()},
            completion_reason=completion_reason,
        )

    async def step(self, state: InMemoryBattleState) -> SimulationStepResult:
        moves = self._collect_moves(state)
        state.ctx.moves_cache = {str(move.char_id): self._move_payload_cache(move) for move in moves}
        state.telemetry.record_moves(moves)

        actions = self.action_collector.collect_actions(state, moves)
        processed_move_ids = await self.executor.process_batch(state.ctx, actions) if actions else []

        state.telemetry.record_executor_context(state.ctx, round_index=state.round_index + 1)
        state.commit_executor_buffers()
        winner = state.winner()
        state.round_index += 1
        return SimulationStepResult(
            processed_move_ids=processed_move_ids,
            action_count=len(actions),
            winner=winner,
        )

    def _collect_moves(self, state: InMemoryBattleState) -> list[CombatMoveDTO]:
        moves: list[CombatMoveDTO] = []
        actors = sorted(state.alive_actors(), key=lambda actor: str(actor.meta.id))
        for actor in actors:
            moves.extend(self.intent_provider.choose_moves(state, actor))
            if len(moves) >= state.limits.max_actions_per_round:
                return moves[: state.limits.max_actions_per_round]
        return moves

    @staticmethod
    def _move_payload_cache(move: CombatMoveDTO) -> dict:
        payload = move.payload.model_dump(mode="json") if hasattr(move.payload, "model_dump") else dict(move.payload)
        payload.setdefault("action", "attack")
        payload.setdefault("strategy", move.strategy)
        payload.setdefault("move_id", move.move_id)
        return payload
