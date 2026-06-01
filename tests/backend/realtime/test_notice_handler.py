from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.backend.realtime import events as events_module


@pytest.mark.unit
async def test_player_notice_handler_delegates_to_notice_service(monkeypatch: pytest.MonkeyPatch) -> None:
    service = SimpleNamespace(deliver=AsyncMock())
    app = SimpleNamespace(state=SimpleNamespace(realtime_notice_service=service))
    monkeypatch.setattr(events_module, "_app", app)

    payload = {"character_ids": "[42]", "template_key": "player.death"}
    await events_module.on_player_notice(payload)

    service.deliver.assert_awaited_once_with(payload)


@pytest.mark.unit
async def test_player_notice_handler_noop_without_app(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(events_module, "_app", None)
    # must not raise when the app is not bound yet
    await events_module.on_player_notice({"character_ids": "[1]"})
