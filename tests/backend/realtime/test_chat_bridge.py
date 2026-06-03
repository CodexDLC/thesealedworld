from __future__ import annotations

import json
import uuid

import pytest

from src.backend.chat.dto.message import IncomingMessageDTO
from src.backend.realtime.services.chat_bridge import (
    ChatBridge,
    ChatEnvelopeAdapter,
    with_session_scope,
)
from tests.backend.realtime.conftest import FakeWebSocket


class FakeMessageService:
    def __init__(self) -> None:
        self.calls: list[tuple[IncomingMessageDTO, uuid.UUID, str]] = []

    async def handle_incoming(
        self, msg: IncomingMessageDTO, sender_id: uuid.UUID, sender_name: str
    ) -> None:
        self.calls.append((msg, sender_id, sender_name))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chat_send_envelope_invokes_message_service() -> None:
    service = FakeMessageService()
    bridge = ChatBridge(service)  # type: ignore[arg-type]
    sender_id = uuid.uuid4()

    await bridge.handle_chat_send(
        {"channel": "global", "content": "hi"},
        sender_id=sender_id,
        sender_name="Ada",
    )

    assert len(service.calls) == 1
    msg, sid, sname = service.calls[0]
    assert msg.channel == "global"
    assert msg.content == "hi"
    assert sid == sender_id
    assert sname == "Ada"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chat_envelope_adapter_wraps_send_text() -> None:
    ws = FakeWebSocket()
    adapter = ChatEnvelopeAdapter(ws)

    await adapter.send_text(json.dumps({"id": "1", "channel": "global", "content": "hi"}))

    assert len(ws.sent) == 1
    decoded = json.loads(ws.sent[0])
    assert decoded == {
        "type": "chat.message",
        "presentation": "chat",
        "payload": {"id": "1", "channel": "global", "content": "hi"},
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chat_envelope_adapter_wraps_send_json() -> None:
    ws = FakeWebSocket()
    adapter = ChatEnvelopeAdapter(ws)

    await adapter.send_json({"id": "2", "channel": "trade", "content": "wts"})

    decoded = json.loads(ws.sent[0])
    assert decoded["type"] == "chat.message"
    assert decoded["payload"]["channel"] == "trade"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chat_envelope_adapter_drops_malformed_input() -> None:
    ws = FakeWebSocket()
    adapter = ChatEnvelopeAdapter(ws)

    await adapter.send_text("not json")

    assert ws.sent == []


@pytest.mark.unit
def test_with_session_scope_backfills_zone_location() -> None:
    msg = IncomingMessageDTO(channel="zone", content="hello")

    scoped = with_session_scope(msg, {"location_id": "52_52"})

    assert scoped is not None
    assert scoped.scope_id == "52_52"


@pytest.mark.unit
def test_with_session_scope_rejects_zone_without_location() -> None:
    msg = IncomingMessageDTO(channel="zone", content="hello")
    assert with_session_scope(msg, {}) is None


@pytest.mark.unit
def test_with_session_scope_passthrough_for_non_zone() -> None:
    msg = IncomingMessageDTO(channel="global", content="hello")
    scoped = with_session_scope(msg, {"location_id": "52_52"})
    assert scoped is msg
    assert scoped.scope_id is None
