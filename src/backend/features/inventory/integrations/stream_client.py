from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.character.events import CharacterEvents

if TYPE_CHECKING:
    from src.backend.core.bus import GameEventProducer


class InventoryStreamClient:
    """Outbound stream client for inventory-owned runtime updates."""

    def __init__(self, events: GameEventProducer) -> None:
        self.events = events

    async def request_gear_score_recalculation(self, *, char_id: int, reason: str) -> None:
        await self.events.publish(
            CharacterEvents.GEAR_SCORE_RECALCULATE_REQUESTED,
            {"char_id": char_id, "reason": reason},
        )


__all__ = ["InventoryStreamClient"]
