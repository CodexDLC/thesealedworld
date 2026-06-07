from __future__ import annotations

from typing import Any

import pytest

from src.backend.features.combat.dto.session import BattleMeta
from src.backend.features.combat.services.turn_manager import CombatTurnManager


class FakeCombatSessions:
    def __init__(self, *, afk_level: int = 0, actor_count: int = 2) -> None:
        self.exchange_moves_data: list[dict[str, Any]] = []
        self.exchange_moves: list[dict[str, Any]] = []
        self.touched_sessions: list[str] = []
        self.started_sessions: list[str] = []
        self.afk_level = afk_level
        self.actor_count = actor_count

    async def get_actor_state(self, session_id: str, char_id: int) -> dict[str, Any]:
        return {"afk_level": self.afk_level, "stamina": 100, "hp": 100, "is_dead": False}

    async def get_battle_meta(self, session_id: str) -> BattleMeta:
        return BattleMeta(
            active=1,
            step_counter=0,
            active_actors_count=self.actor_count,
            teams={
                "team_1": ["1"],
                "team_2": [str(actor_id) for actor_id in range(2, self.actor_count + 1)],
            },
            actors_info={str(actor_id): "player" for actor_id in range(1, self.actor_count + 1)},
            dead_actors=[],
            last_activity_at=0,
            battle_type="pve",
            location_id="test",
        )

    async def register_exchange_move(
        self,
        session_id: str,
        char_id: int,
        target_id: int,
        move_dto: dict[str, Any],
    ) -> bool:
        self.exchange_moves.append(move_dto)
        return True

    async def register_moves_batch(self, session_id: str, char_id: int, exchange_moves_data: list[dict[str, Any]]):
        self.exchange_moves_data.extend(exchange_moves_data)
        return [str(item["move_id"]) for item in exchange_moves_data]

    async def append_moves_batch(self, session_id: str, char_id: int, moves: list[Any]) -> None:
        return None

    async def consume_feint(self, session_id: str, char_id: int, feint_id: str):
        return None

    async def get_targets(self, session_id: str) -> dict[str, list[str]]:
        return {}

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


@pytest.mark.asyncio
async def test_batch_registration_enqueues_timeout_per_accepted_move_id() -> None:
    sessions = FakeCombatSessions()
    arq = FakeArq()
    manager = CombatTurnManager(sessions, arq)  # type: ignore[arg-type]

    await manager.register_moves_batch(
        "combat-1",
        -5,
        [
            {"action": "attack", "target_id": 5},
            {"action": "attack", "target_id": 6},
        ],
    )

    accepted_ids = [item["move_id"] for item in sessions.exchange_moves_data]
    timeout_jobs = [
        payload
        for function, payload, kwargs in arq.jobs
        if function == "combat_collector_task" and payload["signal_type"] == "check_timeout"
    ]

    assert len(timeout_jobs) == 2
    assert [payload["move_id"] for payload in timeout_jobs] == accepted_ids
    assert all(payload["move_id"] != "batch" for payload in timeout_jobs)
    assert all(
        kwargs.get("_defer_until") is not None
        for function, payload, kwargs in arq.jobs
        if function == "combat_collector_task" and payload["signal_type"] == "check_timeout"
    )
    assert sessions.touched_sessions == ["combat-1"]
    assert sessions.started_sessions == ["combat-1"]
    assert [function for function, _, _ in arq.jobs].count("chaos_check_task") == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("afk_level", "expected_timeout_ms"),
    [
        (0, 180_000),
        (1, 90_000),
        (2, 45_000),
    ],
)
async def test_single_move_timeout_scales_with_actor_count_and_stronger_afk_penalty(
    afk_level: int, expected_timeout_ms: int
) -> None:
    sessions = FakeCombatSessions(afk_level=afk_level, actor_count=10)
    arq = FakeArq()
    manager = CombatTurnManager(sessions, arq)  # type: ignore[arg-type]

    await manager.register_move_request("combat-1", 1, {"action": "attack", "target_id": 2})

    assert sessions.exchange_moves[0]["timeout_ms"] == expected_timeout_ms

    timeout_jobs = [
        kwargs
        for function, payload, kwargs in arq.jobs
        if function == "combat_collector_task" and payload["signal_type"] == "check_timeout"
    ]
    assert len(timeout_jobs) == 1
    assert timeout_jobs[0].get("_defer_until") is not None
