from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from src.backend.features.loot import events
from src.backend.features.loot.integrations.stream_client import LootOrderStreamClient


class CapturingEvents:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict[str, Any], str | None]] = []

    async def publish(self, event_type: str, data: dict[str, Any], correlation_id: str | None = None) -> str:
        self.published.append((event_type, data, correlation_id))
        return "1-0"


class FakeLootIntegration:
    saved_pending: list[tuple[str, dict[str, str]]] = []

    def __init__(self, manager: Any, events: Any = None, game_config: Any = None) -> None:
        self.manager = manager
        self.events = events
        self.game_config = game_config

    async def save_pending_actor_corpses(self, session_id: str, corpse_ids_by_actor: dict[str, str]) -> None:
        self.saved_pending.append((session_id, corpse_ids_by_actor))


class FakeLootService:
    calls: list[dict[str, Any]] = []

    def __init__(self, integration: FakeLootIntegration, engine: Any) -> None:
        self.integration = integration

    async def order_loot_for_combat(
        self,
        *,
        session_id: str,
        actors: list[dict[str, Any]],
        location_id: str,
        battle_type: str,
    ) -> dict[str, str]:
        self.calls.append(
            {
                "events": self.integration.events,
                "session_id": session_id,
                "actors": actors,
                "location_id": location_id,
                "battle_type": battle_type,
            }
        )
        return {"wolf_1": "corpse-1"}


@pytest.mark.asyncio
async def test_loot_order_stream_client_publishes_flat_fire_and_forget_payload() -> None:
    app_events = CapturingEvents()
    client = LootOrderStreamClient(app_events)

    await client.order_hidden_corpses(
        session_id="combat-1",
        battle_type="pve",
        location_id="forest",
        actors=[{"actor_id": "wolf_1", "meta": {"type": "monster"}}],
    )

    assert app_events.published == [
        (
            "loot.order_requested",
            {
                "session_id": "combat-1",
                "battle_type": "pve",
                "location_id": "forest",
                "actors_json": json.dumps([{"actor_id": "wolf_1", "meta": {"type": "monster"}}]),
            },
            None,
        )
    ]


@pytest.mark.asyncio
async def test_loot_order_requested_handler_uses_app_events_and_saves_pending_map(monkeypatch) -> None:
    app_events = object()
    app = SimpleNamespace(state=SimpleNamespace(redis=object(), events=app_events))
    FakeLootService.calls = []
    FakeLootIntegration.saved_pending = []

    monkeypatch.setattr(events, "_app", app)
    monkeypatch.setattr(events, "LootManager", lambda redis: object())
    monkeypatch.setattr(events, "LootIntegration", FakeLootIntegration)
    monkeypatch.setattr(events, "LootService", FakeLootService)

    await events.on_order_requested(
        {
            "session_id": "combat-1",
            "battle_type": "pve",
            "location_id": "forest",
            "actors_json": json.dumps([{"actor_id": "wolf_1"}]),
        }
    )

    assert FakeLootService.calls == [
        {
            "events": app_events,
            "session_id": "combat-1",
            "actors": [{"actor_id": "wolf_1"}],
            "location_id": "forest",
            "battle_type": "pve",
        }
    ]
    assert FakeLootIntegration.saved_pending == [("combat-1", {"wolf_1": "corpse-1"})]


class _ExplodingLootService:
    def __init__(self, integration: Any, engine: Any) -> None:
        self.integration = integration

    async def order_loot_for_combat(self, **_kwargs) -> dict[str, str]:
        raise RuntimeError("simulated downstream failure")


@pytest.mark.asyncio
async def test_loot_order_requested_handler_swallows_exceptions(monkeypatch) -> None:
    """Regression: a single broken payload must not poison the stream consumer group."""
    app = SimpleNamespace(state=SimpleNamespace(redis=object(), events=object()))

    monkeypatch.setattr(events, "_app", app)
    monkeypatch.setattr(events, "LootManager", lambda redis: object())
    monkeypatch.setattr(events, "LootIntegration", FakeLootIntegration)
    monkeypatch.setattr(events, "LootService", _ExplodingLootService)

    # Must not raise — handler swallows and logs.
    await events.on_order_requested(
        {
            "session_id": "combat-broken",
            "battle_type": "pve",
            "location_id": "forest",
            "actors_json": json.dumps([{"actor_id": "wolf_1"}]),
        }
    )
