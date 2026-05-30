"""In-memory action collection for simulation runs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast

from src.backend.features.combat.dto.action import CombatActionDTO, CombatMoveDTO
from src.backend.features.combat.runtime.engine.target_resolver import TargetResolver

if TYPE_CHECKING:
    from src.backend.features.combat.runtime.simulation.state import InMemoryBattleState


class SimulationActionCollector:
    """Convert in-memory moves into executor-ready actions."""

    def __init__(self, *, force_unanswered_exchange: bool | None = None) -> None:
        self.force_unanswered_exchange = force_unanswered_exchange
        self.target_resolver = TargetResolver()

    def collect_actions(self, state: InMemoryBattleState, moves: list[CombatMoveDTO]) -> list[CombatActionDTO]:
        actions: list[CombatActionDTO] = []
        actions.extend(
            self._collect_unidirectional_actions(state, [move for move in moves if move.strategy != "exchange"])
        )
        exchange_moves = [move for move in moves if move.strategy == "exchange"]
        actions.extend(self._match_exchange_actions(state, exchange_moves))
        return actions[: state.limits.max_actions_per_round]

    def _match_exchange_actions(
        self,
        state: InMemoryBattleState,
        moves: list[CombatMoveDTO],
    ) -> list[CombatActionDTO]:
        pool: list[tuple[int, CombatMoveDTO]] = list(enumerate(moves))
        by_pair: dict[tuple[str, str], tuple[int, CombatMoveDTO]] = {}
        for order, move in pool:
            target_id = getattr(move.payload, "target_id", None)
            if target_id is not None:
                by_pair.setdefault((str(move.char_id), str(target_id)), (order, move))

        matched_ids: set[str] = set()
        ready_pairs: list[tuple[int, int, CombatActionDTO]] = []
        for order_a, move_a in pool:
            if move_a.move_id in matched_ids:
                continue
            target_id = getattr(move_a.payload, "target_id", None)
            if target_id is None:
                continue
            partner_entry = by_pair.get((str(target_id), str(move_a.char_id)))
            if partner_entry is None:
                continue
            order_b, move_b = partner_entry
            if move_b.move_id == move_a.move_id or move_b.move_id in matched_ids:
                continue
            ready_pairs.append(
                (
                    max(order_a, order_b),
                    min(order_a, order_b),
                    CombatActionDTO(action_type="exchange", move=move_a, partner_move=move_b),
                )
            )
            matched_ids.add(move_a.move_id)
            matched_ids.add(move_b.move_id)

        actions = [action for _ready, _first, action in sorted(ready_pairs, key=lambda item: (item[0], item[1]))]
        if not self._should_force_unanswered(state):
            return actions

        for _order, move in pool:
            if move.move_id in matched_ids:
                continue
            actions.append(CombatActionDTO(action_type="exchange", move=move, is_forced=True))
            matched_ids.add(move.move_id)
        return actions

    def _collect_unidirectional_actions(
        self,
        state: InMemoryBattleState,
        moves: list[CombatMoveDTO],
    ) -> list[CombatActionDTO]:
        actions: list[CombatActionDTO] = []
        for move in moves:
            action_type = cast("Literal['item', 'instant', 'system']", move.strategy)
            payload_target = getattr(move.payload, "target_id", None)
            if move.targets is None and payload_target is not None:
                move = move.model_copy(
                    update={"targets": self.target_resolver.resolve(move.char_id, payload_target, state.ctx.meta)}
                )
            actions.append(CombatActionDTO(action_type=action_type, move=move))
        return actions

    def _should_force_unanswered(self, state: InMemoryBattleState) -> bool:
        if self.force_unanswered_exchange is not None:
            return self.force_unanswered_exchange
        return state.limits.force_unanswered_exchange
