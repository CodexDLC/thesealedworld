from __future__ import annotations

import json

import pytest

from src.backend.chat.services.connection_manager import ChatConnectionManager
from src.backend.realtime.services.connection_manager import (
    CODE_SESSION_REPLACED,
    RealtimeConnectionManager,
)
from tests.backend.realtime.conftest import FakeWebSocket


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_accepts_real_ws_exactly_once() -> None:
    rt = RealtimeConnectionManager()
    chat = ChatConnectionManager()
    ws = FakeWebSocket()

    await rt.connect(
        ws,
        user_id="u",
        character_id=42,
        session_id="s",
        topics=["chat:global"],
        chat_manager=chat,
    )

    assert ws.accept_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_registers_adapter_in_chat_indexes() -> None:
    rt = RealtimeConnectionManager()
    chat = ChatConnectionManager()
    ws = FakeWebSocket()

    entry = await rt.connect(
        ws,
        user_id="u",
        character_id=42,
        session_id="s",
        topics=["chat:global", "chat:trade"],
        chat_manager=chat,
    )

    # realtime indexes hold the real ws
    assert rt.get(42) is entry
    # chat indexes hold the adapter, not the raw ws
    assert entry.adapter in chat._by_topic["chat:global"]
    assert entry.adapter in chat._by_topic["chat:trade"]
    assert ws not in chat._by_topic["chat:global"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_new_connection_for_same_character_replaces_previous() -> None:
    rt = RealtimeConnectionManager()
    chat = ChatConnectionManager()
    ws_old = FakeWebSocket()
    ws_new = FakeWebSocket()

    old_entry = await rt.connect(
        ws_old,
        user_id="u",
        character_id=42,
        session_id="A",
        topics=["chat:global"],
        chat_manager=chat,
    )
    new_entry = await rt.connect(
        ws_new,
        user_id="u",
        character_id=42,
        session_id="B",
        topics=["chat:global"],
        chat_manager=chat,
    )

    assert ws_old.closed == {"code": CODE_SESSION_REPLACED, "reason": "session replaced"}
    assert old_entry.adapter not in chat._by_topic.get("chat:global", set())
    assert new_entry.adapter in chat._by_topic["chat:global"]
    assert rt.get(42) is new_entry
    # old socket received a session_replaced notice payload before close.
    assert any("system.session_replaced" in frame for frame in ws_old.sent)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_replacement_uses_character_id_not_session_id() -> None:
    rt = RealtimeConnectionManager()
    chat = ChatConnectionManager()
    ws_old = FakeWebSocket()
    ws_new = FakeWebSocket()

    await rt.connect(
        ws_old, user_id="u", character_id=42, session_id="same",
        topics=["chat:global"], chat_manager=chat,
    )
    await rt.connect(
        ws_new, user_id="u", character_id=42, session_id="same",
        topics=["chat:global"], chat_manager=chat,
    )

    assert ws_old.closed is not None
    assert rt.active_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_session_replaced_notice_is_best_effort() -> None:
    rt = RealtimeConnectionManager()
    chat = ChatConnectionManager()
    ws_old = FakeWebSocket()
    ws_new = FakeWebSocket()

    await rt.connect(
        ws_old, user_id="u", character_id=42, session_id="A",
        topics=["chat:global"], chat_manager=chat,
    )
    ws_old.send_raises = RuntimeError("client gone")

    await rt.connect(
        ws_new, user_id="u", character_id=42, session_id="B",
        topics=["chat:global"], chat_manager=chat,
    )

    # close still happened despite notice failure; indexes were cleaned.
    assert ws_old.closed == {"code": CODE_SESSION_REPLACED, "reason": "session replaced"}
    assert rt.get(42).ws is ws_new


@pytest.mark.unit
@pytest.mark.asyncio
async def test_disconnect_clears_real_ws_and_adapter() -> None:
    rt = RealtimeConnectionManager()
    chat = ChatConnectionManager()
    ws = FakeWebSocket()

    entry = await rt.connect(
        ws, user_id="u", character_id=42, session_id="s",
        topics=["chat:global", "chat:trade"], chat_manager=chat,
    )

    rt.disconnect(ws, chat)

    assert rt.get(42) is None
    assert rt.active_count == 0
    assert entry.adapter not in chat._by_topic.get("chat:global", set())
    assert entry.adapter not in chat._by_topic.get("chat:trade", set())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_disconnect_after_replacement_does_not_remove_new_entry() -> None:
    rt = RealtimeConnectionManager()
    chat = ChatConnectionManager()
    ws_old = FakeWebSocket()
    ws_new = FakeWebSocket()

    await rt.connect(
        ws_old, user_id="u", character_id=42, session_id="A",
        topics=["chat:global"], chat_manager=chat,
    )
    new_entry = await rt.connect(
        ws_new, user_id="u", character_id=42, session_id="B",
        topics=["chat:global"], chat_manager=chat,
    )

    # Old ws disconnect (race after replacement) must not evict the new entry.
    rt.disconnect(ws_old, chat)

    assert rt.get(42) is new_entry


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chat_broadcast_wraps_payload_via_adapter() -> None:
    rt = RealtimeConnectionManager()
    chat = ChatConnectionManager()
    ws = FakeWebSocket()

    await rt.connect(
        ws, user_id="u", character_id=42, session_id="s",
        topics=["chat:global"], chat_manager=chat,
    )

    await chat.broadcast_topic("chat:global", {"id": "1", "channel": "global", "content": "hi"})

    assert len(ws.sent) == 1
    decoded = json.loads(ws.sent[0])
    assert decoded["type"] == "chat.message"
    assert decoded["presentation"] == "chat"
    assert decoded["payload"]["content"] == "hi"
