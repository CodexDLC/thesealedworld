from __future__ import annotations

import json

import pytest

from src.backend.chat.services.connection_manager import ChatConnectionManager
from src.backend.realtime.integrations.notice_publisher import build_player_notice_payload
from src.backend.realtime.services.connection_manager import RealtimeConnectionManager
from src.backend.realtime.services.notice_service import RealtimeNoticeService
from tests.backend.realtime.conftest import FakeWebSocket


async def _connect(rt: RealtimeConnectionManager, chat: ChatConnectionManager, character_id: int) -> FakeWebSocket:
    ws = FakeWebSocket()
    await rt.connect(
        ws,
        user_id="u",
        character_id=character_id,
        session_id="s",
        topics=["chat:global"],
        chat_manager=chat,
    )
    return ws


@pytest.mark.unit
async def test_send_to_character_delivers_raw_envelope_not_wrapped() -> None:
    rt = RealtimeConnectionManager()
    chat = ChatConnectionManager()
    ws = await _connect(rt, chat, 42)

    delivered = await rt.send_to_character(42, {"type": "player.notice", "presentation": "system_chat", "payload": {}})

    assert delivered is True
    assert len(ws.sent) == 1
    decoded = json.loads(ws.sent[0])
    # delivered directly on the real ws — NOT re-wrapped as chat.message
    assert decoded["type"] == "player.notice"


@pytest.mark.unit
async def test_send_to_character_noop_when_offline() -> None:
    rt = RealtimeConnectionManager()

    delivered = await rt.send_to_character(999, {"type": "player.notice"})

    assert delivered is False


@pytest.mark.unit
async def test_notice_service_builds_envelope_and_fans_out() -> None:
    rt = RealtimeConnectionManager()
    chat = ChatConnectionManager()
    ws = await _connect(rt, chat, 42)
    service = RealtimeNoticeService(rt)

    payload = build_player_notice_payload(
        character_ids=[42],
        template_key="exploration.safe_zone_entered",
        variables={"location": "Город"},
        domain="exploration",
    )
    await service.deliver(payload)

    assert len(ws.sent) == 1
    decoded = json.loads(ws.sent[0])
    assert decoded == {
        "type": "player.notice",
        "presentation": "system_chat",
        "payload": {
            "domain": "exploration",
            "template_key": "exploration.safe_zone_entered",
            "variables": {"location": "Город"},
            "severity": "info",
        },
    }


@pytest.mark.unit
async def test_notice_service_skips_offline_recipients() -> None:
    rt = RealtimeConnectionManager()
    chat = ChatConnectionManager()
    ws = await _connect(rt, chat, 42)
    service = RealtimeNoticeService(rt)

    payload = build_player_notice_payload(
        character_ids=[42, 777],  # 777 offline
        template_key="player.death",
        domain="expedition",
    )
    await service.deliver(payload)

    # only the connected character received a frame; no error for the offline one
    assert len(ws.sent) == 1


@pytest.mark.unit
async def test_notice_service_ignores_empty_recipients() -> None:
    rt = RealtimeConnectionManager()
    service = RealtimeNoticeService(rt)

    await service.deliver({"template_key": "player.death", "character_ids": "[]"})
    # nothing to assert beyond "no exception" — empty recipient list is a no-op
