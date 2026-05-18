from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.backend.features.world.resources.static.d4_city_map import build_d4_city_map_node_metadata
from src.backend.features.world.runtime.config import REGION_ROWS, REGION_SIZE, ZONE_SIZE
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

        # 2. Ensure all D4 zones exist: the static seed now covers the full 15x15 playable map.
        zones_per_region = REGION_SIZE // ZONE_SIZE
        for zx in range(zones_per_region):
            for zy in range(zones_per_region):
                zone_id = f"{region_id}_{zx}_{zy}"
                if await self.data.get_zone(zone_id):
                    continue
                is_hub_zone = zx == 1 and zy == 1
                zone = build_zone_profile(region_profile=region_profile, zone_id=zone_id, zx=zx, zy=zy)
                zone_center_x = _d4_min_x() + zx * ZONE_SIZE + ZONE_SIZE // 2
                zone_center_y = _d4_min_y() + zy * ZONE_SIZE + ZONE_SIZE // 2
                influence = ThreatService.describe(zone_center_x, zone_center_y)
                log.info("Creating Zone %s", zone_id)
                await self.data.upsert_zone(
                    zone_id,
                    region_id=region_id,
                    biome_id=region_profile.biome_id,
                    tier=0 if is_hub_zone else (1 if zx in {0, 2} and zy in {0, 2} else influence.tier),
                    zone_archetype=zone.zone_archetype,
                    navigation_profile_id=zone.navigation_profile_id,
                    landmark_profile=zone.landmark_profile,
                    population_tags=list(zone.population_tags),
                    flags={
                        "is_safe_zone": is_hub_zone,
                        "system_connect": is_hub_zone,
                        "is_hub": is_hub_zone,
                        "portal_shield": is_hub_zone,
                        "is_old_capital": True,
                        "threat_tier": 0 if is_hub_zone else (1 if zx in {0, 2} and zy in {0, 2} else influence.tier),
                    },
                )

        # 3. Prepare nodes for bulk upsert
        nodes_to_upsert = []
        for (x, y), data in static_locations.items():
            content = data.get("content", {})
            tags = content.get("environment_tags", [])

            zone_id = _d4_zone_id(x, y)
            zone_local_x = (x - _d4_min_x()) // ZONE_SIZE
            zone_local_y = (y - _d4_min_y()) // ZONE_SIZE
            zone_profile = build_zone_profile(
                region_profile=region_profile,
                zone_id=zone_id,
                zx=zone_local_x,
                zy=zone_local_y,
            )
            raw_flags = data.get("flags", {})
            is_safe = bool(raw_flags.get("is_safe_zone", False))
            node_type = str(data.get("node_type") or raw_flags.get("node_type") or ("hub" if is_safe else "side_street"))
            terrain_type = str(data.get("terrain_type") or raw_flags.get("terrain_type") or _terrain_type_from_tags(tags))

            nodes_to_upsert.append(
                {
                    "x": x,
                    "y": y,
                    "zone_id": zone_id,
                    "biome_id": region_profile.biome_id,
                    "node_type": node_type,
                    "terrain_type": terrain_type,
                    "navigation_profile_id": zone_profile.navigation_profile_id,
                    "buildable_kind": raw_flags.get("buildable_kind"),
                    "landmark_profile": (
                        zone_profile.landmark_profile if raw_flags.get("is_gate") or raw_flags.get("is_rift") else None
                    ),
                    "movement_profile": self._build_node_movement_profile(
                        raw_movement=data.get("movement_profile", {}),
                        navigation_profile_id=zone_profile.navigation_profile_id,
                        zone_archetype=zone_profile.zone_archetype,
                        node_type=node_type,
                    ),
                    "background_key": data.get("background_key"),
                    "background_pool_key": _background_pool_key(
                        is_safe=is_safe,
                        is_rift=bool(raw_flags.get("is_rift")),
                    ),
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
        flags.setdefault("city_map", build_d4_city_map_node_metadata(x, y))
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


def _d4_min_x() -> int:
    return (4 - 1) * REGION_SIZE


def _d4_min_y() -> int:
    return REGION_ROWS.index("D") * REGION_SIZE


def _d4_zone_id(x: int, y: int) -> str:
    return f"D4_{(x - _d4_min_x()) // ZONE_SIZE}_{(y - _d4_min_y()) // ZONE_SIZE}"


def _terrain_type_from_tags(tags: list[str]) -> str:
    if "hub_center" in tags:
        return "ancient_pavement"
    if "gate" in tags:
        return "city_gate_outer"
    if "outer_monolith_wall" in tags:
        return "outer_monolith_wall_walk"
    if "road" in tags:
        return "ruin_road_main"
    if "ruins" in tags or "city_ruins" in tags:
        return "ruined_foundation"
    return "city_ruins"


def _background_pool_key(*, is_safe: bool, is_rift: bool) -> str:
    if is_rift:
        return "d4_city_rift"
    if is_safe:
        return "d4_hub"
    return "d4_city_ruins"
