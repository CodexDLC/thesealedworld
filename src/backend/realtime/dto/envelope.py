"""Typed envelopes exchanged on the ``/ws/realtime`` socket.

Stage 1 only carries chat traffic. The shapes below also describe the future
``player.notice`` surface so feature owners can target a stable contract when
they migrate (stage 2). Only ``chat.send`` is accepted from the browser today.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

IncomingType = Literal["chat.send", "pong"]
OutgoingType = Literal[
    "chat.message",
    "player.notice",
    "system.session_replaced",
    "ping",
    "error",
]

ChatChannel = Literal["global", "zone", "party", "trade", "system", "dm", "combat"]


class ChatSendPayload(BaseModel):
    """Inner payload for an incoming ``chat.send`` envelope."""

    channel: ChatChannel
    content: str = Field(min_length=1, max_length=500)
    scope_id: str | None = None


class IncomingEnvelopeDTO(BaseModel):
    """Browser → server envelope.

    The ``payload`` is validated by the per-type handler so that adding new
    envelope types in later stages does not require a discriminated union here.
    """

    type: IncomingType
    payload: dict[str, Any] = Field(default_factory=dict)


class OutgoingEnvelopeDTO(BaseModel):
    """Server → browser envelope.

    ``presentation`` is included for forward compatibility with the
    ``player.notice`` surface (`chat`, `system_chat`, `toast`, `modal`,
    `refresh`). Stage 1 only emits `chat` for ``chat.message``.
    """

    type: OutgoingType
    presentation: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
