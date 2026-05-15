from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.core.bus import GameEventProducer


class ExplorationStreamClient:
    ARENA_ENTER_REQUESTED = "arena.session.enter"
    TIMEOUT_SECONDS = 5.0

    def __init__(self, events: GameEventProducer) -> None:
        self.events = events

    async def request_arena_enter(self, char_id: int) -> bool:
        """
        Requests the arena feature to prepare a session for the character.
        Returns True if the arena successfully prepared the entry.
        """
        response = await self.events.request(
            self.ARENA_ENTER_REQUESTED,
            {"char_id": char_id},
            timeout=self.TIMEOUT_SECONDS,
        )
        return isinstance(response, dict) and response.get("status") == "ok"
