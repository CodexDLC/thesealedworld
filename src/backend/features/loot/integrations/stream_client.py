from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.core.bus import GameEventProducer

LOOT_ORDER_REQUESTED = "loot.order_requested"


class LootOrderStreamClient:
    """Outbound stream client for asynchronous loot ordering."""

    def __init__(self, events: GameEventProducer) -> None:
        self.events = events

    async def order_hidden_corpses(
        self,
        *,
        session_id: str,
        battle_type: str,
        location_id: str,
        actors: list[dict[str, Any]],
    ) -> None:
        await self.events.publish(
            LOOT_ORDER_REQUESTED,
            {
                "session_id": session_id,
                "battle_type": battle_type,
                "location_id": location_id,
                "actors_json": json.dumps(actors),
            },
        )
