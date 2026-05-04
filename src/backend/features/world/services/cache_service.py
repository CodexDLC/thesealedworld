from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.backend.features.world.services.navigation_service import WorldNavigationService

if TYPE_CHECKING:
    from src.backend.infrastructure.world.managers.location_store import WorldLocationStore
    from src.backend.infrastructure.world.models import WorldGrid
    from src.backend.infrastructure.world.repositories import WorldRepository

log = logging.getLogger(__name__)


class WorldCacheService:
    def __init__(
        self,
        repository: WorldRepository,
        locations: WorldLocationStore,
        navigation: WorldNavigationService | None = None,
    ) -> None:
        self.repository = repository
        self.locations = locations
        self.navigation = navigation or WorldNavigationService()

    async def warm_runtime_cache(self) -> int:
        active_nodes = await self.repository.get_active_nodes()
        node_map = {self._loc_id(node): node for node in active_nodes}
        payload = {self._loc_id(node): self._to_location_cache(node, node_map) for node in active_nodes}
        count = await self.locations.write_locations(payload)
        log.info("World cache warmed: active_nodes=%s cached=%s", len(active_nodes), count)
        return count

    def _to_location_cache(self, node: WorldGrid, node_map: dict[str, WorldGrid]) -> dict[str, Any]:
        loc_id = self._loc_id(node)
        content = node.content or {}
        flags = node.flags if isinstance(node.flags, dict) else {}
        services = node.services if isinstance(node.services, list) else []
        return {
            "loc_id": loc_id,
            "name": content.get("title", f"Узел {loc_id}"),
            "description": content.get("description", "..."),
            "exits": self.navigation.calculate_exits(node, node_map),
            "tags": content.get("environment_tags", []),
            "service": services[0] if services else "",
            "services": services,
            "flags": flags,
            "zone_id": str(node.zone_id),
            "terrain": str(node.terrain_type),
        }

    @staticmethod
    def _loc_id(node: WorldGrid) -> str:
        return f"{node.x}_{node.y}"
