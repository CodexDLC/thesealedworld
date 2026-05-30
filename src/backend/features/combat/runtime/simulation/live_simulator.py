"""Live-like in-memory combat simulation loop."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.backend.features.combat.dto.action import CombatActionDTO, CombatMoveDTO
from src.backend.features.combat.dto.ids import ActorId, ActorIdLike, normalize_actor_id
from src.backend.features.combat.dto.payloads import ExchangePayload, InstantPayload
from src.backend.features.combat.runtime.ai.brain import MonsterCombatBrain
from src.backend.features.combat.runtime.processors.executor import CombatExecutor
from src.backend.features.combat.runtime.simulation.simulator import SimulationRunResult

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorSnapshot
    from src.backend.features.combat.runtime.simulation.state import InMemoryBattleState

LiveStepCallback = Callable[["LiveSimulationStepResult", "InMemoryBattleState"], Awaitable[None]]


@dataclass(frozen=True)
class LiveSimulationTiming:
    tick_interval_seconds: float = 0.05
    max_ticks: int = 500
    timeout_ticks: int | None = 8
    use_wall_clock_delay: bool = False
    base_decision_ticks: int = 10
    min_decision_ticks: int = 1


@dataclass(frozen=True)
class LiveSimulationStepResult:
    tick_index: int
    exchange_index: int
    registered_move_id: str | None
    processed_move_ids: list[str]
    action_count: int
    winner: str | None
    timeout_forced: bool = False


class SimulationMoveRegistrar:
    """In-memory equivalent of register_exchange_move_atomic."""

    def register_exchange_move(
        self,
        state: InMemoryBattleState,
        move: CombatMoveDTO,
        pending_moves: dict[str, CombatMoveDTO],
    ) -> bool:
        target_id = getattr(move.payload, "target_id", None)
        if target_id is None:
            return False

        actor = state.ctx.get_actor(move.char_id)
        target = state.ctx.get_actor(target_id)
        if actor is None or target is None or not actor.is_alive or not target.is_alive:
            return False

        target_queue = state.ctx.targets.setdefault(actor.meta.id, [])
        index = self._target_index(target_queue, target_id)
        if index is None:
            return False

        target_queue.pop(index)
        pending_moves[move.move_id] = move
        self.refresh_moves_cache(state, pending_moves)
        return True

    def refresh_moves_cache(self, state: InMemoryBattleState, pending_moves: dict[str, CombatMoveDTO]) -> None:
        cache: dict[str, dict[str, Any]] = {}
        for move in pending_moves.values():
            cache[str(move.char_id)] = self._move_payload_cache(move)
        state.ctx.moves_cache = cache

    @staticmethod
    def _target_index(target_queue: list[ActorIdLike], target_id: ActorIdLike) -> int | None:
        normalized = str(target_id)
        for index, candidate in enumerate(target_queue):
            if str(candidate) == normalized:
                return index
        return None

    @staticmethod
    def _move_payload_cache(move: CombatMoveDTO) -> dict[str, Any]:
        payload = move.payload.model_dump(mode="json") if hasattr(move.payload, "model_dump") else dict(move.payload)
        payload.setdefault("action", "attack")
        payload.setdefault("strategy", move.strategy)
        payload.setdefault("move_id", move.move_id)
        return payload


class LiveInMemoryCombatSimulator:
    """Resolve one registered exchange per combat step, with visible ticks."""

    def __init__(
        self,
        *,
        executor: CombatExecutor | None = None,
        brain: MonsterCombatBrain | None = None,
        registrar: SimulationMoveRegistrar | None = None,
        timing: LiveSimulationTiming | None = None,
    ) -> None:
        self.executor = executor or CombatExecutor()
        self.brain = brain or MonsterCombatBrain()
        self.registrar = registrar or SimulationMoveRegistrar()
        self.timing = timing or LiveSimulationTiming()
        self._pending_moves: dict[str, CombatMoveDTO] = {}
        self._move_registered_tick: dict[str, int] = {}
        self._next_decision_tick: dict[str, int] = {}

    async def run(
        self,
        state: InMemoryBattleState,
        *,
        on_step: LiveStepCallback | None = None,
    ) -> SimulationRunResult:
        winner = state.winner()
        tick_index = 0
        while (
            winner is None
            and state.ctx.meta.step_counter < state.limits.max_rounds
            and tick_index < self.timing.max_ticks
        ):
            step = await self.step(state, tick_index=tick_index)
            winner = step.winner
            if on_step is not None:
                await on_step(step, state)
            tick_index = self._next_tick_index(state, current_tick=tick_index + 1)
            if winner is not None:
                break
            if self.timing.use_wall_clock_delay and self.timing.tick_interval_seconds > 0:
                import asyncio

                await asyncio.sleep(self.timing.tick_interval_seconds)

        completion_reason = "victory"
        if winner is None:
            winner = "draw"
            completion_reason = (
                "max_exchanges_reached"
                if state.ctx.meta.step_counter >= state.limits.max_rounds
                else "max_ticks_reached"
            )
        state.ctx.meta.winner = winner
        state.ctx.meta.active = 0
        return SimulationRunResult(
            winner=winner,
            rounds_completed=state.ctx.meta.step_counter,
            telemetry=state.telemetry,
            final_hp_by_actor={str(actor_id): actor.meta.hp for actor_id, actor in state.ctx.actors.items()},
            completion_reason=completion_reason,
        )

    async def step(self, state: InMemoryBattleState, *, tick_index: int) -> LiveSimulationStepResult:
        registered_move_id, instant_processed_ids = await self._try_register_next_move(state, tick_index=tick_index)
        action = self._ready_exchange_action()
        timeout_forced = False
        if action is None:
            action = self._timeout_action(tick_index=tick_index)
            timeout_forced = action is not None

        processed_move_ids: list[str] = list(instant_processed_ids)
        if action is not None:
            processed_move_ids.extend(await self.executor.process_batch(state.ctx, [action]))
            self._remove_processed_moves(action)
            state.telemetry.record_executor_context(state.ctx, round_index=state.ctx.meta.step_counter)
            state.commit_executor_buffers()
            self.registrar.refresh_moves_cache(state, self._pending_moves)

        winner = state.winner()
        return LiveSimulationStepResult(
            tick_index=tick_index,
            exchange_index=state.ctx.meta.step_counter,
            registered_move_id=registered_move_id,
            processed_move_ids=processed_move_ids,
            action_count=1 if action is not None else 0,
            winner=winner,
            timeout_forced=timeout_forced,
        )

    async def _try_register_next_move(
        self,
        state: InMemoryBattleState,
        *,
        tick_index: int,
    ) -> tuple[str | None, list[str]]:
        actor = self._next_actor_ready_with_target(state, tick_index=tick_index)
        if actor is None:
            return None, []

        target_queue = [
            target_id for target_id in state.ctx.targets.get(actor.meta.id, []) if state.ctx.get_actor(target_id)
        ]
        candidates = [state.ctx.get_actor(target_id) for target_id in target_queue[: state.limits.candidate_limit]]
        candidates = [candidate for candidate in candidates if candidate is not None and candidate.is_alive]
        if not candidates:
            return None, []

        payloads = self.brain.decide_turn(actor, state.ctx, candidates[:1])
        if not payloads:
            return None, []

        instant_processed_ids = await self._process_instant_payloads(
            state,
            actor,
            tick_index=tick_index,
            payloads=[payload for payload in payloads if payload.get("action") == "instant"],
        )
        exchange_payload = next((payload for payload in payloads if payload.get("action") != "instant"), None)
        if exchange_payload is None:
            return None, instant_processed_ids
        target_id = exchange_payload.get("target_id") or str(candidates[0].meta.id)
        move = CombatMoveDTO(
            move_id=f"live-{tick_index}-{actor.meta.id}-{target_id}",
            char_id=normalize_actor_id(actor.meta.id),
            strategy="exchange",
            payload=ExchangePayload(target_id=normalize_actor_id(target_id), feint_id=exchange_payload.get("feint_id")),
        )
        accepted = self.registrar.register_exchange_move(state, move, self._pending_moves)
        if not accepted:
            return None, instant_processed_ids
        self._move_registered_tick[move.move_id] = tick_index
        self._next_decision_tick[str(actor.meta.id)] = tick_index + self._decision_delay(actor)
        state.telemetry.record_moves([move])
        return move.move_id, instant_processed_ids

    async def _process_instant_payloads(
        self,
        state: InMemoryBattleState,
        actor: ActorSnapshot,
        *,
        tick_index: int,
        payloads: list[dict[str, Any]],
    ) -> list[str]:
        processed_ids: list[str] = []
        for index, payload in enumerate(payloads):
            ability_id = payload.get("ability_id")
            target_id = payload.get("target_id")
            if not ability_id or target_id is None:
                continue
            move = CombatMoveDTO(
                move_id=f"live-{tick_index}-{actor.meta.id}-instant-{index}",
                char_id=normalize_actor_id(actor.meta.id),
                strategy="instant",
                payload=InstantPayload(ability_id=ability_id, target_id=target_id),
            )
            state.telemetry.record_moves([move])
            processed_ids.extend(
                await self.executor.process_batch(
                    state.ctx,
                    [CombatActionDTO(action_type="instant", move=move)],
                )
            )
            state.telemetry.record_executor_context(state.ctx, round_index=state.ctx.meta.step_counter)
            state.commit_executor_buffers()
        return processed_ids

    def _next_actor_ready_with_target(self, state: InMemoryBattleState, *, tick_index: int) -> ActorSnapshot | None:
        candidates = [
            actor
            for actor in state.alive_actors()
            if self._has_live_target(state, actor) and self._actor_ready_at(actor) <= tick_index
        ]
        return min(candidates, key=lambda actor: self._actor_priority(state, actor)) if candidates else None

    def _next_tick_index(self, state: InMemoryBattleState, *, current_tick: int) -> int:
        if self._ready_exchange_action() is not None:
            return current_tick
        ready_tick = min(
            (self._actor_ready_at(actor) for actor in state.alive_actors() if self._has_live_target(state, actor)),
            default=current_tick,
        )
        timeout_tick = min(
            (
                registered_at + self.timing.timeout_ticks
                for registered_at in self._move_registered_tick.values()
                if self.timing.timeout_ticks is not None
            ),
            default=current_tick,
        )
        return max(current_tick, min(ready_tick, timeout_tick))

    def _actor_priority(self, state: InMemoryBattleState, actor: ActorSnapshot) -> tuple[int, float, int, str]:
        return (
            self._actor_ready_at(actor),
            -self._initiative(actor),
            self._stable_jitter(state.seed, actor.meta.id),
            str(actor.meta.id),
        )

    def _actor_ready_at(self, actor: ActorSnapshot) -> int:
        return int(self._next_decision_tick.get(str(actor.meta.id), self._initial_decision_tick(actor)))

    def _initial_decision_tick(self, actor: ActorSnapshot) -> int:
        return self._decision_delay(actor)

    def _decision_delay(self, actor: ActorSnapshot) -> int:
        initiative = max(self._initiative(actor), 0.0)
        scaled = self.timing.base_decision_ticks / (1.0 + initiative / 100.0)
        return max(int(self.timing.min_decision_ticks), int(math.ceil(scaled)))

    @staticmethod
    def _initiative(actor: ActorSnapshot) -> float:
        if actor.stats is None:
            return 0.0
        return float(actor.stats.mods.initiative or 0.0)

    @staticmethod
    def _stable_jitter(seed: int, actor_id: ActorId) -> int:
        payload = f"{seed}|{actor_id}".encode()
        return int.from_bytes(hashlib.blake2b(payload, digest_size=4).digest(), "big")

    @staticmethod
    def _has_live_target(state: InMemoryBattleState, actor: ActorSnapshot) -> bool:
        for target_id in state.ctx.targets.get(actor.meta.id, []):
            target = state.ctx.get_actor(target_id)
            if target is not None and target.is_alive:
                return True
        return False

    def _ready_exchange_action(self) -> CombatActionDTO | None:
        for move in self._pending_moves.values():
            partner = self._partner_move(move)
            if partner is not None:
                return CombatActionDTO(action_type="exchange", move=move, partner_move=partner)
        return None

    def _timeout_action(self, *, tick_index: int) -> CombatActionDTO | None:
        if self.timing.timeout_ticks is None:
            return None
        for move in self._pending_moves.values():
            registered_at = self._move_registered_tick.get(move.move_id, tick_index)
            if tick_index - registered_at >= self.timing.timeout_ticks:
                return CombatActionDTO(action_type="exchange", move=move, is_forced=True)
        return None

    def _partner_move(self, move: CombatMoveDTO) -> CombatMoveDTO | None:
        target_id = getattr(move.payload, "target_id", None)
        if target_id is None:
            return None
        for candidate in self._pending_moves.values():
            if candidate.move_id == move.move_id:
                continue
            candidate_target = getattr(candidate.payload, "target_id", None)
            if str(candidate.char_id) == str(target_id) and str(candidate_target) == str(move.char_id):
                return candidate
        return None

    def _remove_processed_moves(self, action: CombatActionDTO) -> None:
        ids = [action.move.move_id]
        if action.partner_move is not None:
            ids.append(action.partner_move.move_id)
        for move_id in ids:
            self._pending_moves.pop(move_id, None)
            self._move_registered_tick.pop(move_id, None)


__all__ = [
    "LiveInMemoryCombatSimulator",
    "LiveSimulationStepResult",
    "LiveSimulationTiming",
    "SimulationMoveRegistrar",
]
