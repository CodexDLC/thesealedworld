"""Bridge between the realtime gateway and the chat module.

Two responsibilities:

* :class:`ChatEnvelopeAdapter` wraps every outgoing chat dictionary in a typed
  ``chat.message`` envelope before it hits the wire. It is the *only* sink the
  realtime gateway registers into :class:`ChatConnectionManager` — the real
  FastAPI ``WebSocket`` is never registered there directly, so chat fan-out
  cannot accidentally write a raw payload.
* :class:`ChatBridge` translates the inbound ``chat.send`` envelope into an
  :class:`IncomingMessageDTO` and forwards it to :class:`MessageService`.

The adapter intentionally does **not** subclass FastAPI's WebSocket — chat
fan-out only calls ``await sink.send_text(data)``, so the duck-typed surface
below is enough.
"""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING, Any

from src.backend.chat.dto.message import IncomingMessageDTO
from src.backend.realtime.dto.envelope import ChatSendPayload

if TYPE_CHECKING:
    from fastapi import WebSocket

    from src.backend.chat.services.message_service import MessageService


def _wrap_chat_message(payload: dict[str, Any]) -> str:
    return json.dumps(
        {"type": "chat.message", "presentation": "chat", "payload": payload},
        default=str,
    )


class ChatEnvelopeAdapter:
    """Duck-typed sink that wraps chat payloads as ``chat.message`` envelopes.

    Registered into :class:`ChatConnectionManager` topic indexes in place of the
    real socket. The real ``WebSocket`` is owned by
    :class:`RealtimeConnectionManager`; this adapter never accepts or closes
    the underlying socket on its own — it just rewrites bytes on the way out.
    """

    __slots__ = ("_ws",)

    def __init__(self, ws: WebSocket) -> None:
        self._ws = ws

    @property
    def ws(self) -> WebSocket:
        return self._ws

    async def send_text(self, data: str) -> None:
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            # Malformed chat data must not reach the browser un-wrapped.
            return
        if not isinstance(payload, dict):
            return
        await self._ws.send_text(_wrap_chat_message(payload))

    async def send_json(self, payload: dict[str, Any]) -> None:
        await self._ws.send_text(_wrap_chat_message(payload))


class ChatBridge:
    """Routes inbound ``chat.send`` envelopes to :class:`MessageService`."""

    def __init__(self, message_service: MessageService) -> None:
        self._message_service = message_service

    async def handle_chat_send(
        self,
        payload: dict[str, Any],
        *,
        sender_id: uuid.UUID,
        sender_name: str,
    ) -> None:
        validated = ChatSendPayload.model_validate(payload)
        msg = IncomingMessageDTO(
            channel=validated.channel,
            content=validated.content,
            scope_id=validated.scope_id,
        )
        await self._message_service.handle_incoming(msg, sender_id, sender_name)


def with_session_scope(msg: IncomingMessageDTO, state: dict[str, Any]) -> IncomingMessageDTO | None:
    """Backfill ``scope_id`` for zone messages from the cached player session.

    Ported verbatim from the deleted ``chat/api/ws.py`` so the existing chat
    semantics (and its dedicated test coverage) are preserved.
    """
    if msg.channel != "zone" or msg.scope_id:
        return msg
    location_id = state.get("location_id")
    if not location_id:
        return None
    return msg.model_copy(update={"scope_id": str(location_id)})
