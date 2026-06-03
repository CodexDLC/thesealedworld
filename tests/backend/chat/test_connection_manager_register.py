"""Accept-less register/unregister surface on ChatConnectionManager.

Added so the realtime gateway can attach an envelope-wrapping adapter into
chat topic indexes without re-accepting the underlying socket. See
``src/backend/realtime/services/connection_manager.py``.
"""

from __future__ import annotations

import json

import pytest

from src.backend.chat.services.connection_manager import ChatConnectionManager


class _Sink:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_text(self, data: str) -> None:
        self.sent.append(data)


@pytest.mark.unit
def test_register_indexes_sink_under_topics_and_user() -> None:
    chat = ChatConnectionManager()
    sink = _Sink()

    chat.register(sink, ["chat:global", "chat:trade"], user_id="user-1")

    assert sink in chat._by_topic["chat:global"]
    assert sink in chat._by_topic["chat:trade"]
    assert sink in chat._by_user["user-1"]


@pytest.mark.unit
def test_unregister_drops_sink_from_all_indexes() -> None:
    chat = ChatConnectionManager()
    sink = _Sink()
    chat.register(sink, ["chat:global"], user_id="user-1")

    chat.unregister(sink)

    assert "chat:global" not in chat._by_topic
    assert "user-1" not in chat._by_user


@pytest.mark.unit
@pytest.mark.asyncio
async def test_broadcast_topic_reaches_registered_sink() -> None:
    chat = ChatConnectionManager()
    sink = _Sink()
    chat.register(sink, ["chat:global"])

    await chat.broadcast_topic("chat:global", {"content": "hello"})

    assert len(sink.sent) == 1
    assert json.loads(sink.sent[0]) == {"content": "hello"}


@pytest.mark.unit
def test_subscribe_user_extends_topics_for_registered_sink() -> None:
    chat = ChatConnectionManager()
    sink = _Sink()
    chat.register(sink, ["chat:global"], user_id="user-1")

    chat.subscribe_user("user-1", "chat:dm:new-session")

    assert sink in chat._by_topic["chat:dm:new-session"]
