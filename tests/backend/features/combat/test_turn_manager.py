from __future__ import annotations

from typing import Any

import pytest

from src.backend.features.combat.services.turn_manager import CombatTurnManager


class FakeCombatSessions:
    def __init__(self) -> None:
        self.exchange_moves_data: list[dict[str, Any]] = []
        self.touched_sessions: list[str] = []

    async def register_moves_batch(self, session_id: str, char_id: int, exchange_moves_data: list[dict[str, Any]]):
        self.exchange_moves_data.extend(exchange_moves_data)
        return [str(item["move_id"]) for item in exchange_moves_data]

    async def append_moves_batch(self, session_id: str, char_id: int, moves: list[Any]) -> None:
        return None

    async def consume_feint(self, session_id: str, char_id: int, feint_id: str):
        return None

    async def touch_activity(self, session_id: str) -> None:
        self.touched_sessions.append(session_id)


class FakeArq:
    def __init__(self) -> None:
        self.jobs: list[tuple[str, dict[str, Any], dict[str, Any]]] = []

    async def enqueue_job(self, function: str, payload: dict[str, Any], **kwargs: Any) -> None:
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
    timeout_jobs = [payload for _, payload, kwargs in arq.jobs if payload["signal_type"] == "check_timeout"]

    assert len(timeout_jobs) == 2
    assert [payload["move_id"] for payload in timeout_jobs] == accepted_ids
    assert all(payload["move_id"] != "batch" for payload in timeout_jobs)
    assert all(kwargs.get("_defer_until") is not None for _, payload, kwargs in arq.jobs if payload["signal_type"] == "check_timeout")
    assert sessions.touched_sessions == ["combat-1"]
