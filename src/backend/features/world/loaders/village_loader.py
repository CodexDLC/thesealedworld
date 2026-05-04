from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.backend.infrastructure.world.models import WorldRegion, WorldZone

if TYPE_CHECKING:
    from src.backend.infrastructure.world.repositories import WorldRepository

log = logging.getLogger(__name__)


class VillageLoader:
    """Service to load static village data into the world database."""

    def __init__(self, repository: WorldRepository) -> None:
        self.repository = repository

    async def load_village(self, static_locations: dict[tuple[int, int], dict[str, Any]]) -> int:
        """Loads static locations into the WorldGrid.
        
        Automatically creates region D4 and zone D4_hub if they don't exist.
        """
        # 1. Ensure Region D4 exists
        region_id = "D4"
        region = await self.repository.get_region(region_id)
        if not region:
            log.info("Creating Region %s", region_id)
            await self.repository.upsert_region(WorldRegion(id=region_id, climate_tags=["city_ruins", "ancient"]))

        # 2. Ensure Zone D4_hub exists
        zone_id = "D4_hub"
        zone = await self.repository.get_zone(zone_id)
        if not zone:
            log.info("Creating Zone %s", zone_id)
            await self.repository.upsert_zone(
                WorldZone(
                    id=zone_id,
                    region_id=region_id,
                    biome_id="city_ruins",
                    tier=0,
                    flags={"is_safe_zone": True, "is_hub": True},
                )
            )

        # 3. Prepare nodes for bulk upsert
        nodes_to_upsert = []
        for (x, y), data in static_locations.items():
            content = data.get("content", {})
            tags = content.get("environment_tags", [])
            
            # Simple heuristic for terrain_type
            terrain_type = "ancient_pavement"
            if "hub_center" in tags:
                terrain_type = "ancient_pavement"
            elif "gate" in tags:
                terrain_type = "city_gate_outer"
            elif "ruins" in tags:
                terrain_type = "ruined_foundation"

            nodes_to_upsert.append({
                "x": x,
                "y": y,
                "zone_id": zone_id,
                "terrain_type": terrain_type,
                "services": data.get("services", []),
                "content": content,
                "is_active": data.get("is_active", True),
                "flags": data.get("flags", {}),
            })

        if nodes_to_upsert:
            await self.repository.bulk_upsert_nodes(nodes_to_upsert)
            log.info("Successfully upserted %d village nodes", len(nodes_to_upsert))
            return len(nodes_to_upsert)
        
        return 0
