from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.infrastructure.world.models import WorldGrid
    from src.backend.infrastructure.world.repositories import WorldRepository


@dataclass(slots=True)
class WorldZoneSeed:
    id: str
    region_id: str
    biome_id: str
    tier: int
    flags: dict[str, Any]


class WorldDataIntegration:
    """World-owned facade over persistent generated world data."""

    def __init__(self, repository: WorldRepository) -> None:
        self.repository = repository

    async def has_world_data(self) -> bool:
        return await self.repository.has_world_data()

    async def count_active_nodes(self) -> int:
        return await self.repository.count_active_nodes()

    async def get_active_nodes(self) -> list[WorldGrid]:
        return await self.repository.get_active_nodes()

    async def region_exists(self, region_id: str) -> bool:
        return await self.repository.get_region(region_id) is not None

    async def get_zone(self, zone_id: str) -> WorldZoneSeed | None:
        zone = await self.repository.get_zone(zone_id)
        if zone is None:
            return None
        return WorldZoneSeed(
            id=str(zone.id),
            region_id=str(zone.region_id),
            biome_id=str(zone.biome_id),
            tier=int(zone.tier),
            flags=dict(zone.flags or {}),
        )

    async def upsert_region(self, region_id: str, *, climate_tags: list[str]) -> None:
        await self.repository.upsert_region(region_id, climate_tags=climate_tags)

    async def upsert_zone(
        self,
        zone_id: str,
        *,
        region_id: str,
        biome_id: str,
        tier: int,
        flags: dict[str, Any],
    ) -> None:
        await self.repository.upsert_zone(
            zone_id,
            region_id=region_id,
            biome_id=biome_id,
            tier=tier,
            flags=flags,
        )

    async def save_zone_lore(self, zone: WorldZoneSeed, *, lore_name: str, lore_background: str) -> None:
        flags = dict(zone.flags)
        flags["lore_name"] = lore_name
        flags["lore_background"] = lore_background
        await self.upsert_zone(
            zone.id,
            region_id=zone.region_id,
            biome_id=zone.biome_id,
            tier=zone.tier,
            flags=flags,
        )

    async def flush(self) -> None:
        await self.repository.flush()

    async def get_nodes_in_rect(self, x: int, y: int, width: int, height: int) -> list[WorldGrid]:
        return await self.repository.get_nodes_in_rect(x, y, width, height)

    async def bulk_upsert_nodes(self, nodes: list[dict[str, Any]]) -> None:
        await self.repository.bulk_upsert_nodes(nodes)

    async def create_or_update_node(
        self,
        *,
        x: int,
        y: int,
        zone_id: str,
        terrain_type: str,
        is_active: bool = False,
        flags: dict[str, Any] | None = None,
        content: dict[str, Any] | None = None,
        services: list[str] | None = None,
    ) -> None:
        await self.repository.create_or_update_node(
            x=x,
            y=y,
            zone_id=zone_id,
            terrain_type=terrain_type,
            is_active=is_active,
            flags=flags,
            content=content,
            services=services,
        )

    async def update_flags(self, x: int, y: int, new_flags: dict[str, Any], *, activate_node: bool = False) -> bool:
        return await self.repository.update_flags(x, y, new_flags, activate_node=activate_node)

    async def update_content(self, x: int, y: int, content: dict[str, Any]) -> bool:
        return await self.repository.update_content(x, y, content)
