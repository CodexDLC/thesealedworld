from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.backend.features.world.runtime.theme import WorldThemeService
from src.backend.features.world.runtime.threat import ThreatService

if TYPE_CHECKING:
    from collections.abc import Mapping

    from src.backend.features.world.integrations import WorldDataIntegration

log = logging.getLogger(__name__)


class VillageLoader:
    """Service to load static village data into the world database."""

    def __init__(self, data: WorldDataIntegration) -> None:
        self.data = data

    async def load_village(self, static_locations: Mapping[tuple[int, int], Any]) -> int:
        """Loads static locations into the WorldGrid.

        Automatically creates region D4 and hub zone D4_1_1 if they don't exist.
        """
        # 1. Ensure Region D4 exists
        region_id = "D4"
        if not await self.data.region_exists(region_id):
            log.info("Creating Region %s", region_id)
            await self.data.upsert_region(region_id, climate_tags=["city_ruins", "ancient", "portal_shield"])

        # 2. Ensure hub zone exists
        zone_id = "D4_1_1"
        if not await self.data.get_zone(zone_id):
            log.info("Creating Zone %s", zone_id)
            await self.data.upsert_zone(
                zone_id,
                region_id=region_id,
                biome_id="city_ruins",
                tier=0,
                flags={"is_safe_zone": True, "is_hub": True, "portal_shield": True, "threat_tier": 0},
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

            nodes_to_upsert.append(
                {
                    "x": x,
                    "y": y,
                    "zone_id": zone_id,
                    "terrain_type": terrain_type,
                    "services": data.get("services", []),
                    "content": content,
                    "is_active": data.get("is_active", True),
                    "flags": self._build_node_flags(x, y, data.get("flags", {})),
                }
            )

        if nodes_to_upsert:
            await self.data.bulk_upsert_nodes(nodes_to_upsert)
            log.info("Successfully upserted %d village nodes", len(nodes_to_upsert))
            return len(nodes_to_upsert)

        return 0

    @staticmethod
    def _build_node_flags(x: int, y: int, raw_flags: dict[str, Any]) -> dict[str, Any]:
        influence = ThreatService.describe(x, y)
        flags = dict(raw_flags)
        flags.setdefault("threat_tier", influence.tier)
        flags["anchor_influence"] = {
            "threat": influence.threat,
            "tier": influence.tier,
            "dominant_anchor": influence.dominant_anchor,
            "tags": influence.tags,
            "is_inside_city_shield": influence.is_inside_city_shield,
        }
        flags["world_theme"] = WorldThemeService.build(x, y, loc_id=f"{x}_{y}").model_dump(mode="json")
        return flags
