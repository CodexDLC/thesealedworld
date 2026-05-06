from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.features.world.integrations import WorldLocationIntegration


class WorldService:
    def __init__(self, locations: WorldLocationIntegration) -> None:
        self.locations = locations

    async def get_location(self, loc_id: str) -> dict[str, Any] | None:
        return await self.locations.get_location(loc_id)

    async def register_battle(self, loc_id: str, battle_id: str, description: str) -> None:
        await self.locations.register_battle(loc_id, battle_id, description)

    async def unregister_battle(self, loc_id: str, battle_id: str) -> None:
        await self.locations.unregister_battle(loc_id, battle_id)
