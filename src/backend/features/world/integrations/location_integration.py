from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.infrastructure.world.location_store import WorldLocationStore


class WorldLocationIntegration:
    """World-owned facade over the runtime location cache/store."""

    def __init__(self, store: WorldLocationStore) -> None:
        self.store = store

    async def write_locations(self, locations: dict[str, dict[str, Any]]) -> int:
        return await self.store.write_locations(locations)

    async def get_location(self, loc_id: str) -> dict[str, Any] | None:
        return await self.store.get_location(loc_id)

    async def location_exists(self, loc_id: str) -> bool:
        return await self.store.location_exists(loc_id)

    async def add_player(self, loc_id: str, char_id: int) -> None:
        await self.store.add_player(loc_id, char_id)

    async def remove_player(self, loc_id: str, char_id: int) -> None:
        await self.store.remove_player(loc_id, char_id)

    async def get_players(self, loc_id: str) -> set[str]:
        return await self.store.get_players(loc_id)

    async def register_battle(self, loc_id: str, battle_id: str, description: str) -> None:
        await self.store.add_battle(loc_id, battle_id, description)

    async def unregister_battle(self, loc_id: str, battle_id: str) -> None:
        await self.store.remove_battle(loc_id, battle_id)

    async def get_battles(self, loc_id: str) -> dict[str, str]:
        return await self.store.get_battles(loc_id)
