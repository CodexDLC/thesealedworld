from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.backend.features.world.services.navigation_service import WorldNavigationNode, WorldNavigationService

if TYPE_CHECKING:
    from collections.abc import Mapping

    from src.backend.features.world.integrations import WorldDataIntegration, WorldLocationIntegration

log = logging.getLogger(__name__)


class WorldCacheService:
    def __init__(
        self,
        data: WorldDataIntegration,
        locations: WorldLocationIntegration,
        navigation: WorldNavigationService | None = None,
    ) -> None:
        self.data = data
        self.locations = locations
        self.navigation = navigation or WorldNavigationService()

    async def warm_runtime_cache(self) -> int:
        active_nodes = await self.data.get_active_nodes()
        node_map = {self._loc_id(node): node for node in active_nodes}
        payload = {self._loc_id(node): self._to_location_cache(node, node_map) for node in active_nodes}
        count = await self.locations.write_locations(payload)
        log.info("World cache warmed: active_nodes=%s cached=%s", len(active_nodes), count)
        return count

    def _to_location_cache(
        self, node: WorldNavigationNode, node_map: Mapping[str, WorldNavigationNode]
    ) -> dict[str, Any]:
        loc_id = self._loc_id(node)
        content = node.content or {}
        flags = node.flags if isinstance(node.flags, dict) else {}
        anchor_influence = flags.get("anchor_influence", {})
        world_theme = flags.get("world_theme", {})
        cached_flags = self._cache_flags(flags)
        services = node.services if isinstance(node.services, list) else []
        world_zone = self._world_zone(node)
        return {
            "loc_id": loc_id,
            "name": content.get("title", f"Узел {loc_id}"),
            "description": content.get("description", "..."),
            "background_url": content.get("background_url"),
            "background_key": getattr(node, "background_key", None),
            "background_pool_key": getattr(node, "background_pool_key", None),
            "visual_overrides": _safe_dict(getattr(node, "visual_overrides", None)),
            "anchor_influence": anchor_influence if isinstance(anchor_influence, dict) else {},
            "world_theme": world_theme if isinstance(world_theme, dict) else {},
            "exits": self.navigation.calculate_exits(node, node_map),
            "tags": content.get("environment_tags", []),
            "service": services[0] if services else "",
            "services": services,
            "flags": cached_flags,
            "zone_id": str(node.zone_id),
            "world_zone": world_zone,
            "biome_id": _safe_text(getattr(node, "biome_id", None), fallback=world_zone["biome_id"]),
            "node_type": _safe_text(getattr(node, "node_type", None), fallback="generic"),
            "navigation_profile_id": _safe_text(getattr(node, "navigation_profile_id", None)),
            "buildable_kind": getattr(node, "buildable_kind", None),
            "landmark_profile": getattr(node, "landmark_profile", None),
            "movement_profile": _safe_dict(getattr(node, "movement_profile", None)),
            "terrain": str(node.terrain_type),
        }

    @staticmethod
    def _loc_id(node: WorldNavigationNode) -> str:
        return f"{node.x}_{node.y}"

    @staticmethod
    def _cache_flags(flags: dict[str, Any]) -> dict[str, Any]:
        cached = dict(flags)
        cached.pop("anchor_influence", None)
        cached.pop("world_theme", None)
        return cached

    @staticmethod
    def _world_zone(node: WorldNavigationNode) -> dict[str, Any]:
        zone = getattr(node, "zone", None)
        return {
            "id": _safe_text(getattr(zone, "id", None), fallback=str(node.zone_id)),
            "region_id": _safe_text(getattr(zone, "region_id", None)),
            "biome_id": _safe_text(getattr(zone, "biome_id", None)),
            "tier": _safe_int(getattr(zone, "tier", 0)),
            "zone_archetype": _safe_text(getattr(zone, "zone_archetype", None)),
            "navigation_profile_id": _safe_text(getattr(zone, "navigation_profile_id", None)),
            "landmark_profile": getattr(zone, "landmark_profile", None),
            "population_tags": _safe_list(getattr(zone, "population_tags", None)),
            "flags": _safe_dict(getattr(zone, "flags", None)),
        }


def _safe_text(value: Any, *, fallback: str = "") -> str:
    return value if isinstance(value, str) and value else fallback


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []
