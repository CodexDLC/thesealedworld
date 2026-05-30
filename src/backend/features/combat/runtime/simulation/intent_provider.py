"""Simulation intent providers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from src.backend.features.combat.dto.action import CombatMoveDTO
from src.backend.features.combat.dto.ids import normalize_actor_id
from src.backend.features.combat.dto.payloads import ExchangePayload, InstantPayload
from src.backend.features.combat.runtime.ai.brain import MonsterCombatBrain

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorSnapshot
    from src.backend.features.combat.runtime.simulation.state import InMemoryBattleState


class SimulationIntentProvider(Protocol):
    """Generates in-memory combat moves for one actor."""

    def choose_moves(self, state: InMemoryBattleState, actor: ActorSnapshot) -> list[CombatMoveDTO]: ...


class AiSimulationIntentProvider:
    """Use MonsterCombatBrain as the temporary decision model for every actor."""

    def __init__(self, brain: MonsterCombatBrain | None = None, *, candidate_limit: int | None = None) -> None:
        self.brain = brain or MonsterCombatBrain()
        self.candidate_limit = candidate_limit

    def choose_moves(self, state: InMemoryBattleState, actor: ActorSnapshot) -> list[CombatMoveDTO]:
        candidates = self._candidate_targets(state, actor)
        if not candidates:
            return []

        payloads = self.brain.decide_turn(actor, state.ctx, candidates)
        moves: list[CombatMoveDTO] = []
        for index, payload in enumerate(payloads):
            target_id = payload.get("target_id")
            if target_id is None:
                continue
            if payload.get("action") == "instant":
                moves.append(
                    CombatMoveDTO(
                        move_id=f"sim-{state.round_index}-{actor.meta.id}-instant-{index}",
                        char_id=normalize_actor_id(actor.meta.id),
                        strategy="instant",
                        payload=InstantPayload(
                            ability_id=payload.get("ability_id"),
                            target_id=target_id,
                        ),
                    )
                )
                continue
            moves.append(
                CombatMoveDTO(
                    move_id=f"sim-{state.round_index}-{actor.meta.id}-{index}",
                    char_id=normalize_actor_id(actor.meta.id),
                    strategy="exchange",
                    payload=ExchangePayload(
                        target_id=target_id,
                        feint_id=payload.get("feint_id"),
                    ),
                )
            )
        return moves

    def _candidate_targets(self, state: InMemoryBattleState, actor: ActorSnapshot) -> list[ActorSnapshot]:
        limit = self.candidate_limit if self.candidate_limit is not None else state.limits.candidate_limit
        enemies = [enemy for enemy in state.ctx.get_enemies(actor.meta.id) if enemy.is_alive]
        enemies.sort(key=lambda enemy: (enemy.meta.hp, str(enemy.meta.id)))
        return enemies[: max(1, int(limit))]
