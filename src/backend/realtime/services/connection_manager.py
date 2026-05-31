"""WebSocket lifecycle and uniqueness for ``/ws/realtime``.

The realtime manager is the *only* site that calls ``ws.accept()``. The chat
fan-out registry receives an envelope-wrapping adapter, never the raw socket,
so chat broadcast can never write an un-wrapped payload to the wire.

Uniqueness is keyed on ``character_id``. A new valid connection for an
already-connected character closes the previous socket with code ``4002`` —
``session_id`` is recorded for diagnostics, not used as the replacement key.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from loguru import logger

from src.backend.realtime.services.chat_bridge import ChatEnvelopeAdapter

if TYPE_CHECKING:
    from fastapi import WebSocket

    from src.backend.chat.services.connection_manager import ChatConnectionManager

CODE_SESSION_REPLACED = 4002


@dataclass
class RealtimeEntry:
    """Live registration for one ``/ws/realtime`` connection."""

    ws: WebSocket
    adapter: ChatEnvelopeAdapter
    user_id: str
    character_id: int
    session_id: str
    topics: set[str] = field(default_factory=set)


class RealtimeConnectionManager:
    """Owns ``ws.accept()`` and one-socket-per-character uniqueness."""

    def __init__(self) -> None:
        self._by_character: dict[int, RealtimeEntry] = {}
        self._by_ws: dict[Any, RealtimeEntry] = {}

    @property
    def active_count(self) -> int:
        return len(self._by_ws)

    def get(self, character_id: int) -> RealtimeEntry | None:
        return self._by_character.get(character_id)

    async def connect(
        self,
        ws: WebSocket,
        *,
        user_id: str,
        character_id: int,
        session_id: str,
        topics: list[str],
        chat_manager: ChatConnectionManager,
    ) -> RealtimeEntry:
        """Accept ``ws`` exactly once, evict any previous socket for the same character."""
        await ws.accept()

        existing = self._by_character.get(character_id)
        if existing is not None:
            await self._evict(existing, chat_manager)

        adapter = ChatEnvelopeAdapter(ws)
        chat_manager.register(adapter, topics, user_id=user_id)

        entry = RealtimeEntry(
            ws=ws,
            adapter=adapter,
            user_id=user_id,
            character_id=character_id,
            session_id=session_id,
            topics=set(topics),
        )
        self._by_character[character_id] = entry
        self._by_ws[ws] = entry
        return entry

    def disconnect(self, ws: Any, chat_manager: ChatConnectionManager) -> None:
        """Drop ``ws`` from both registries. Caller owns the actual close()."""
        entry = self._by_ws.pop(ws, None)
        if entry is None:
            return
        chat_manager.unregister(entry.adapter)
        # Only drop the character index if it still points at this entry — a
        # newer connection may have already replaced it.
        if self._by_character.get(entry.character_id) is entry:
            del self._by_character[entry.character_id]

    async def _evict(self, entry: RealtimeEntry, chat_manager: ChatConnectionManager) -> None:
        """Close a replaced connection and drop it from indexes."""
        chat_manager.unregister(entry.adapter)
        self._by_ws.pop(entry.ws, None)
        if self._by_character.get(entry.character_id) is entry:
            del self._by_character[entry.character_id]
        try:
            await entry.ws.send_text(json.dumps({"type": "system.session_replaced", "payload": {}}))
        except Exception:
            # Best-effort notice. Correctness depends on close code + cleanup.
            logger.bind(character_id=entry.character_id).debug("RealtimeSessionReplacedNoticeFailed")
        try:
            await entry.ws.close(code=CODE_SESSION_REPLACED, reason="session replaced")
        except Exception:
            logger.bind(character_id=entry.character_id).debug("RealtimeSessionReplacedCloseFailed")
