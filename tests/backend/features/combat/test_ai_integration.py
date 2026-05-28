"""Integration tests for the AI runtime path.

Covers two pieces that unit tests previously missed:

1. ``CombatTurnManager.register_moves_batch`` must NOT register an exchange
   whose feint failed ``consume_feint`` — historically the move was appended
   to the batch list before consumption was attempted, leaving a stale
   intent registered with a feint that was never deducted.

2. ``ai_turn_task`` must prefer ``decide_turn`` over per-target
   ``decide_exchange`` and forward the produced payloads to
   ``register_moves_batch``.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.backend.features.combat.dto.actor import (
    ActorLoadoutDTO,
    ActorMetaDTO,
    ActorRawDTO,
    ActorSnapshot,
    ActorStats,
    FeintHandDTO,
)
from src.backend.features.combat.dto.session import BattleContext, BattleMeta
from src.backend.features.combat.services.turn_manager import CombatTurnManager
from src.backend.features.combat.workers.tasks.ai_turn_task import ai_turn_task
from src.shared.schemas.modifier_dto import CombatModifiersDTO, CombatSkillsDTO


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeCombatSessions:
    """Minimal stand-in for the session integration used by TurnManager.

    Records what was registered and exposes a programmable
    ``consume_feint`` so tests can simulate "feint not available".
    """

    def __init__(
        self,
        feint_costs: dict[str, dict[str, int]] | None = None,
        rejected_target_ids: set[Any] | None = None,
    ) -> None:
        self.feint_costs = dict(feint_costs or {})
        self.registered_batches: list[list[dict[str, Any]]] = []
        self.appended_other_moves: list[Any] = []
        self.touched_sessions: list[str] = []
        self.started_sessions: list[str] = []
        self.consume_calls: list[str] = []
        self.returned_feints: list[tuple[str, dict[str, int]]] = []
        # If a registered move's target_id (compared as str) is in this set,
        # the atomic Lua script "rejects" it (e.g. target died between
        # consume and batch registration). Those move_ids are NOT returned
        # in accepted_move_ids, which triggers the refund path in
        # CombatTurnManager.
        self._rejected_target_ids = {str(tid) for tid in (rejected_target_ids or ())}

    async def register_moves_batch(self, session_id: str, char_id: int, exchange_moves_data: list[dict[str, Any]]):
        self.registered_batches.append(list(exchange_moves_data))
        accepted: list[str] = []
        for item in exchange_moves_data:
            if str(item["target_id"]) in self._rejected_target_ids:
                continue
            accepted.append(str(item["move_id"]))
        return accepted

    async def append_moves_batch(self, session_id: str, char_id: int, moves: list[Any]) -> None:
        self.appended_other_moves.extend(moves)

    async def consume_feint(self, session_id: str, char_id: int, feint_id: str):
        self.consume_calls.append(feint_id)
        return self.feint_costs.get(feint_id)

    async def return_feint(
        self, session_id: str, char_id: int, feint_id: str, cost: dict[str, int]
    ) -> None:
        # Record refund call and restore the cost map so subsequent
        # consume_feint observes the feint as available again.
        self.returned_feints.append((feint_id, dict(cost)))
        self.feint_costs[feint_id] = dict(cost)

    async def touch_activity(self, session_id: str) -> None:
        self.touched_sessions.append(session_id)

    async def mark_started_and_refresh_ttl(self, session_id: str) -> bool:
        if session_id in self.started_sessions:
            return False
        self.started_sessions.append(session_id)
        return True


class FakeArq:
    def __init__(self) -> None:
        self.jobs: list[tuple[str, Any, dict[str, Any]]] = []

    async def enqueue_job(self, function: str, payload: Any, **kwargs: Any) -> None:
        self.jobs.append((function, payload, kwargs))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _actor(
    actor_id: str,
    *,
    team: str,
    hp: int = 100,
    stamina: int = 60,
    hand: dict[str, dict[str, int]] | None = None,
    mods: dict[str, float] | None = None,
    is_ai: bool = False,
) -> ActorSnapshot:
    feints = FeintHandDTO(hand=dict(hand or {}), arsenal=list((hand or {}).keys()))
    meta = ActorMetaDTO(
        id=actor_id,
        name=actor_id,
        type="monster" if is_ai else "player",
        team=team,
        is_ai=is_ai,
        hp=hp,
        max_hp=max(hp, 1),
        stamina=stamina,
        max_stamina=max(stamina, 1),
        tokens={},
        feints=feints,
    )
    stats = ActorStats(
        mods=CombatModifiersDTO(**(mods or {})),
        skills=CombatSkillsDTO(),
    )
    return ActorSnapshot(
        meta=meta,
        raw=ActorRawDTO(),
        skills={},
        loadout=ActorLoadoutDTO(),
        stats=stats,
    )


def _battle(actors: list[ActorSnapshot]) -> BattleContext:
    return BattleContext(
        session_id="combat-int-1",
        meta=BattleMeta(
            active=1,
            step_counter=0,
            active_actors_count=len(actors),
            teams={
                "red": [a.meta.id for a in actors if a.meta.team == "red"],
                "blue": [a.meta.id for a in actors if a.meta.team == "blue"],
            },
            battle_type="arena",
            location_id="arena",
        ),
        actors={str(a.meta.id): a for a in actors},
    )


# ---------------------------------------------------------------------------
# P1 — register_moves_batch must not register a move whose feint was not
#      consumed.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_skips_move_when_consume_feint_returns_none() -> None:
    """Stale / duplicate AI task simulates consume_feint returning None.

    Before the fix the move was appended to ``exchange_moves_data`` before
    consumption was attempted; after the fix the failed consume short-circuits
    the iteration *before* the batch list is touched.
    """
    sessions = FakeCombatSessions(feint_costs={})  # consume_feint will return None
    arq = FakeArq()
    manager = CombatTurnManager(sessions, arq)  # type: ignore[arg-type]

    await manager.register_moves_batch(
        "combat-int-1",
        -7,
        [
            {"action": "attack", "target_id": 5, "feint_id": "sword_blade_bind"},
            {"action": "attack", "target_id": 6},
        ],
    )

    assert sessions.consume_calls == ["sword_blade_bind"]
    # Exactly one batch register call, with the no-feint move only.
    assert len(sessions.registered_batches) == 1
    registered_targets = [str(item["target_id"]) for item in sessions.registered_batches[0]]
    assert registered_targets == ["6"]


@pytest.mark.asyncio
async def test_batch_keeps_move_when_consume_feint_succeeds() -> None:
    sessions = FakeCombatSessions(
        feint_costs={"sword_blade_bind": {"hit": 3, "parry": 2}}
    )
    arq = FakeArq()
    manager = CombatTurnManager(sessions, arq)  # type: ignore[arg-type]

    await manager.register_moves_batch(
        "combat-int-1",
        -7,
        [
            {"action": "attack", "target_id": 5, "feint_id": "sword_blade_bind"},
            {"action": "attack", "target_id": 6},
        ],
    )

    assert sessions.consume_calls == ["sword_blade_bind"]
    registered_targets = [str(item["target_id"]) for item in sessions.registered_batches[0]]
    assert registered_targets == ["5", "6"]


# ---------------------------------------------------------------------------
# Integration — ai_turn_task prefers decide_turn and forwards to manager.
# ---------------------------------------------------------------------------


class CapturingTurnManager:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any, list[dict[str, Any]]]] = []

    async def register_moves_batch(
        self, session_id: str, char_id: Any, payloads: list[dict[str, Any]]
    ) -> None:
        self.calls.append((session_id, char_id, list(payloads)))


class FakeDataService:
    def __init__(self, battle: BattleContext) -> None:
        self._battle = battle

    async def load_battle_context(self, session_id: str) -> BattleContext:
        return self._battle


class RecordingAiProcessor:
    def __init__(self, payloads_per_turn: list[dict[str, Any]] | None = None) -> None:
        self.turn_calls: list[tuple[str, list[str]]] = []
        self.exchange_calls: list[tuple[str, str]] = []
        self._next_payloads = payloads_per_turn or []

    def decide_turn(
        self,
        bot: ActorSnapshot,
        battle: BattleContext,
        candidate_targets: list[ActorSnapshot],
    ) -> list[dict[str, Any]]:
        self.turn_calls.append(
            (str(bot.meta.id), [str(t.meta.id) for t in candidate_targets])
        )
        return list(self._next_payloads)

    def decide_exchange(self, bot: ActorSnapshot, target: ActorSnapshot) -> dict[str, Any]:
        self.exchange_calls.append((str(bot.meta.id), str(target.meta.id)))
        return {"action": "attack", "target_id": str(target.meta.id)}


@pytest.mark.asyncio
async def test_ai_turn_task_uses_decide_turn_and_forwards_payloads() -> None:
    bot = _actor("bot1", team="red", is_ai=True)
    target_a = _actor("p1", team="blue")
    target_b = _actor("p2", team="blue")
    battle = _battle([bot, target_a, target_b])

    expected_payloads = [
        {"action": "attack", "target_id": "p1", "feint_id": "measured_strike"},
        {"action": "attack", "target_id": "p2"},
    ]
    turn_manager = CapturingTurnManager()
    processor = RecordingAiProcessor(payloads_per_turn=expected_payloads)
    data_service = FakeDataService(battle)

    ctx = {
        "turn_manager": turn_manager,
        "ai_processor": processor,
        "combat_data_service": data_service,
    }
    request = {"session_id": battle.session_id, "bot_id": "bot1", "missing_targets": ["p1", "p2"]}

    await ai_turn_task(ctx, request)

    assert processor.turn_calls == [("bot1", ["p1", "p2"])]
    assert processor.exchange_calls == []  # fallback path not used
    assert len(turn_manager.calls) == 1
    session_id, char_id, payloads = turn_manager.calls[0]
    assert session_id == battle.session_id
    assert str(char_id) == "bot1"
    assert payloads == expected_payloads


@pytest.mark.asyncio
async def test_ai_turn_task_falls_back_to_decide_exchange_when_decide_turn_returns_empty() -> None:
    bot = _actor("bot1", team="red", is_ai=True)
    target_a = _actor("p1", team="blue")
    target_b = _actor("p2", team="blue")
    battle = _battle([bot, target_a, target_b])

    turn_manager = CapturingTurnManager()
    processor = RecordingAiProcessor(payloads_per_turn=[])  # forces fallback
    data_service = FakeDataService(battle)

    ctx = {
        "turn_manager": turn_manager,
        "ai_processor": processor,
        "combat_data_service": data_service,
    }
    request = {"session_id": battle.session_id, "bot_id": "bot1", "missing_targets": ["p1", "p2"]}

    await ai_turn_task(ctx, request)

    assert processor.exchange_calls == [("bot1", "p1"), ("bot1", "p2")]
    assert len(turn_manager.calls) == 1
    _, _, payloads = turn_manager.calls[0]
    assert [p["target_id"] for p in payloads] == ["p1", "p2"]


# ---------------------------------------------------------------------------
# Refund: move_id consumed but not accepted by Lua → feint must be returned.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_refunds_feint_when_lua_rejects_move_id() -> None:
    """consume_feint succeeded but the atomic registration rejected the
    intent (e.g. target died between consume and Lua). The feint must be
    returned to the hand so the bot is not punished for an outcome it
    could not control.
    """
    sessions = FakeCombatSessions(
        feint_costs={"sword_blade_bind": {"hit": 3, "parry": 2}},
        rejected_target_ids={5},  # Lua rejects intent vs target 5
    )
    arq = FakeArq()
    manager = CombatTurnManager(sessions, arq)  # type: ignore[arg-type]

    await manager.register_moves_batch(
        "combat-int-1",
        -7,
        [
            {"action": "attack", "target_id": 5, "feint_id": "sword_blade_bind"},
            {"action": "attack", "target_id": 6},
        ],
    )

    # consume_feint was called once.
    assert sessions.consume_calls == ["sword_blade_bind"]
    # Both moves were submitted to the batch.
    assert len(sessions.registered_batches) == 1
    submitted_targets = [str(item["target_id"]) for item in sessions.registered_batches[0]]
    assert submitted_targets == ["5", "6"]
    # The rejected move's feint was returned to the hand.
    refunded_ids = [feint_id for feint_id, _ in sessions.returned_feints]
    assert refunded_ids == ["sword_blade_bind"]
    refunded_costs = [cost for _, cost in sessions.returned_feints]
    assert refunded_costs == [{"hit": 3, "parry": 2}]


@pytest.mark.asyncio
async def test_batch_does_not_refund_when_lua_accepts_all() -> None:
    """Happy path: no rejection, no refund."""
    sessions = FakeCombatSessions(
        feint_costs={"sword_blade_bind": {"hit": 3, "parry": 2}},
    )
    arq = FakeArq()
    manager = CombatTurnManager(sessions, arq)  # type: ignore[arg-type]

    await manager.register_moves_batch(
        "combat-int-1",
        -7,
        [{"action": "attack", "target_id": 5, "feint_id": "sword_blade_bind"}],
    )

    assert sessions.returned_feints == []
