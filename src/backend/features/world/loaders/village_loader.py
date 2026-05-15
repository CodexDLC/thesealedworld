from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.backend.features.world.runtime.geography import WorldGeographyService
from src.backend.features.world.runtime.profiles import build_region_profile, build_zone_profile
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
        region_influence = ThreatService.describe(52, 52)
        region_profile = build_region_profile(
            region_id=region_id,
            center_x=52,
            center_y=52,
            geography=WorldGeographyService.describe_zone(52, 52),
            influence=region_influence,
        )
        zone_profile = build_zone_profile(region_profile=region_profile, zone_id="D4_1_1", zx=1, zy=1)
        if not await self.data.region_exists(region_id):
            log.info("Creating Region %s", region_id)
            await self.data.upsert_region(
                region_id,
                climate_tags=list(region_profile.region_tags),
                context={"region_profile": region_profile.model_dump()},
                biome_id=region_profile.biome_id,
                biome_mix=region_profile.biome_mix,
                region_archetype=region_profile.region_archetype,
                tier_min=region_profile.tier_band[0],
                tier_max=region_profile.tier_band[1],
                navigation_profile_id=region_profile.navigation_profile_id,
                population_profile=region_profile.population_profile.model_dump(),
                anchor_influence=region_profile.anchor_influence,
                is_locked_frontier=region_profile.is_locked_frontier,
            )

        # 2. Ensure hub zone exists
        zone_id = "D4_1_1"
        if not await self.data.get_zone(zone_id):
            log.info("Creating Zone %s", zone_id)
            await self.data.upsert_zone(
                zone_id,
                region_id=region_id,
                biome_id=region_profile.biome_id,
                tier=0,
                zone_archetype=zone_profile.zone_archetype,
                navigation_profile_id=zone_profile.navigation_profile_id,
                landmark_profile=zone_profile.landmark_profile,
                population_tags=list(zone_profile.population_tags),
                flags={
                    "is_safe_zone": True,
                    "system_connect": True,
                    "is_hub": True,
                    "portal_shield": True,
                    "threat_tier": 0,
                },
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
                    "biome_id": region_profile.biome_id,
                    "node_type": "hub",
                    "terrain_type": terrain_type,
                    "navigation_profile_id": zone_profile.navigation_profile_id,
                    "buildable_kind": None,
                    "landmark_profile": zone_profile.landmark_profile,
                    "movement_profile": self._build_node_movement_profile(
                        raw_movement=data.get("movement_profile", {}),
                        navigation_profile_id=zone_profile.navigation_profile_id,
                        zone_archetype=zone_profile.zone_archetype,
                        node_type="hub",
                    ),
                    "background_key": data.get("background_key"),
                    "background_pool_key": "d4_hub",
                    "visual_overrides": data.get("visual_overrides", {}),
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
        if flags.get("is_safe_zone"):
            flags.setdefault("system_connect", True)
        flags["anchor_influence"] = {
            "threat": influence.threat,
            "tier": influence.tier,
            "dominant_anchor": influence.dominant_anchor,
            "tags": influence.tags,
            "is_inside_city_shield": influence.is_inside_city_shield,
        }
        flags["world_theme"] = WorldThemeService.build(x, y, loc_id=f"{x}_{y}").model_dump(mode="json")
        return flags

    @staticmethod
    def _build_node_movement_profile(
        *,
        raw_movement: dict[str, Any],
        navigation_profile_id: str,
        zone_archetype: str,
        node_type: str,
    ) -> dict[str, Any]:
        blocked_exits = raw_movement.get("blocked_exits", [])
        gated_exits = raw_movement.get("gated_exits", {})
        return {
            "navigation_profile_id": navigation_profile_id,
            "zone_archetype": zone_archetype,
            "node_type": node_type,
            "is_passable": bool(raw_movement.get("is_passable", True)),
            "has_road": bool(raw_movement.get("has_road", False)),
            "travel_cost": _travel_cost(raw_movement),
            "blocked_exits": list(blocked_exits) if isinstance(blocked_exits, list) else [],
            "gated_exits": dict(gated_exits) if isinstance(gated_exits, dict) else {},
        }


def _travel_cost(raw_movement: dict[str, Any]) -> float:
    try:
        return max(1.0, float(raw_movement.get("travel_cost", 1.0)))
    except (TypeError, ValueError):
        return 1.0
