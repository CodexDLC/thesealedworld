from types import SimpleNamespace
from typing import Any

import pytest

from src.backend.features.combat import events


class FailingArqQueue:
    async def enqueue_job(self, *args: Any, **kwargs: Any) -> None:
        raise AssertionError("session creation must not enqueue chaos watchdog")


class CapturingEvents:
    def __init__(self) -> None:
        self.replies: list[tuple[str, dict[str, Any], int]] = []

    async def publish_reply(self, correlation_id: str, payload: dict[str, Any], *, ttl: int) -> None:
        self.replies.append((correlation_id, payload, ttl))


class FakeCreationOrchestrator:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    async def create_from_request(self, request_data: dict[str, Any]) -> dict[str, Any]:
        return {"combat_id": "combat-1", "status": "ready"}


@pytest.mark.asyncio
async def test_session_requested_does_not_enqueue_chaos_watchdog(monkeypatch) -> None:
    app_events = CapturingEvents()
    app = SimpleNamespace(
        state=SimpleNamespace(
            redis=object(),
            actor_commitments=object(),
            character_sessions=object(),
            events=app_events,
            combat_arq=FailingArqQueue(),
        )
    )
    monkeypatch.setattr(events.CombatSessionIntegration, "from_redis", lambda redis: object())
    monkeypatch.setattr(events, "CombatLifecycleService", lambda store: object())
    monkeypatch.setattr(events, "CombatSystemIntegrator", lambda **kwargs: object())
    monkeypatch.setattr(events, "CombatCreationOrchestrator", FakeCreationOrchestrator)
    monkeypatch.setattr(events, "_app", app)

    await events.on_session_requested({"correlation_id": "corr-1"})

    assert app_events.replies == [("corr-1", {"combat_id": "combat-1", "status": "ready"}, 30)]
