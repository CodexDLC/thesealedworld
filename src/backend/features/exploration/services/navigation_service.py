from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from src.backend.features.exploration.dto.config import ExplorationConfig
from src.backend.features.exploration.dto.result import MoveResolution
from src.backend.features.exploration.runtime.navigation import NavigationEngine
from src.shared.schemas.exploration import (
    AlertHudDTO,
    ExplorationHudDTO,
    NavigationActionsDTO,
    WorldNavigationDTO,
)
from src.shared.schemas.world_theme import WorldThemeDTO

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.backend.features.exploration.integrations.system_integrator import ExplorationSystemIntegrator


class ExplorationNavigationService:
    """Owns movement validation and navigation payload assembly."""

    def __init__(self, integrator: ExplorationSystemIntegrator) -> None:
        self._integrator = integrator

    async def resolve_move(
        self,
        char_id: int,
        *,
        direction: str | None = None,
        target_id: str | None = None,
    ) -> MoveResolution:
        current_loc_id = await self.current_loc_id(char_id)
        current_loc_data = await self.location_data(current_loc_id)
        exits = current_loc_data.get("exits", {})
        target_loc_id = self._resolve_target(exits, direction=direction, target_id=target_id)
        if target_loc_id is None:
            return MoveResolution(
                current_loc_id=current_loc_id,
                current_loc_data=current_loc_data,
                allowed=False,
                message="Переход недоступен.",
            )

        target_loc_data = await self.location_data(target_loc_id)
        if not target_loc_data:
            log.warning("ExplorationNavigationService | target_not_found char_id=%s target=%s", char_id, target_loc_id)
            return MoveResolution(
                current_loc_id=current_loc_id,
                current_loc_data=current_loc_data,
                target_loc_id=target_loc_id,
                allowed=False,
                message="Локация недоступна.",
            )

        return MoveResolution(
            current_loc_id=current_loc_id,
            current_loc_data=current_loc_data,
            target_loc_id=target_loc_id,
            target_loc_data=target_loc_data,
            allowed=True,
        )

    async def move_player(self, char_id: int, resolution: MoveResolution) -> bool:
        if not resolution.allowed or resolution.target_loc_id is None:
            return False
        return await self._integrator.move_player(char_id, resolution.current_loc_id, resolution.target_loc_id)

    async def current_loc_id(self, char_id: int) -> str:
        return await self._integrator.get_player_location_id(char_id) or ExplorationConfig.DEFAULT_SPAWN_POINT

    async def location_data(self, loc_id: str) -> dict[str, Any]:
        return await self._integrator.get_location_data(loc_id) or {}

    async def build_current_navigation(
        self,
        char_id: int,
        *,
        alert: AlertHudDTO | None = None,
    ) -> WorldNavigationDTO:
        loc_id = await self.current_loc_id(char_id)
        loc_data = await self.location_data(loc_id)
        return await self.build_navigation(char_id, loc_id, loc_data, alert=alert)

    async def build_navigation(
        self,
        char_id: int,
        loc_id: str,
        loc_data: dict[str, Any],
        *,
        alert: AlertHudDTO | None = None,
    ) -> WorldNavigationDTO:
        players_count = await self._integrator.get_players_count(loc_id, exclude_char_id=char_id)
        battles = await self._integrator.get_battles(loc_id)
        flags = loc_data.get("flags", {})
        flags = flags if isinstance(flags, dict) else {}
        anchor_influence = loc_data.get("anchor_influence", {})
        anchor_influence = anchor_influence if isinstance(anchor_influence, dict) else {}
        world_theme = WorldThemeDTO.model_validate(loc_data.get("world_theme") or {})
        if world_theme.loc_id is None:
            world_theme.loc_id = loc_id

        exits = loc_data.get("exits", {})
        exits = exits if isinstance(exits, dict) else {}
        world_zone = loc_data.get("world_zone", {})
        world_zone = world_zone if isinstance(world_zone, dict) else {}
        grid = NavigationEngine.build_grid(loc_id, exits, flags, anchor_influence)
        navigation = self._build_navigation_actions(loc_id, exits, flags, anchor_influence)
        is_safe_zone = NavigationEngine.is_safe_context(flags, anchor_influence)
        risk_getter = getattr(self._integrator, "get_risk_state", None)
        risk = await risk_getter(char_id) if risk_getter is not None else {}
        threat = self._safe_threat(anchor_influence.get("threat", flags.get("threat", 0.0)))

        hud: ExplorationHudDTO | AlertHudDTO = alert or ExplorationHudDTO(
            threat=threat,
            threat_tier=int(flags.get("threat_tier", 0)),
            players_count=players_count,
            battles_count=len(battles),
            is_safe_zone=is_safe_zone,
            system_connect=bool(flags.get("system_connect") or flags.get("is_safe_zone", False)),
            risk_state=str(risk.get("sync_state", "safe")),
            pending_free_xp=float(risk.get("pending_free_xp", 0.0) or 0.0),
            pending_skill_count=int(risk.get("pending_skill_count", 0) or 0),
            carried_resource_count=int(risk.get("carried_resource_count", 0) or 0),
            carried_item_count=int(risk.get("carried_item_count", 0) or 0),
            dominant_anchor=anchor_influence.get("dominant_anchor"),
            ambient_tags=anchor_influence.get("tags", []),
        )
        dto = WorldNavigationDTO(
            loc_id=loc_id,
            title=loc_data.get("name", "Unknown"),
            description=loc_data.get("description", "..."),
            background_url=self._resolve_background_url(loc_data),
            anchor_influence=anchor_influence,
            world_theme=world_theme,
            visual_objects=[],
            players_nearby=players_count,
            grid=grid,
            navigation=navigation,
            hud=hud,
            threat_tier=int(flags.get("threat_tier", 0)),
            is_safe_zone=is_safe_zone,
            zone_id=str(loc_data.get("zone_id") or world_zone.get("id") or ""),
            terrain=str(loc_data.get("terrain") or ""),
            biome_id=str(loc_data.get("biome_id") or world_zone.get("biome_id") or ""),
            node_type=str(loc_data.get("node_type") or ""),
            zone_archetype=str(world_zone.get("zone_archetype") or ""),
            navigation_profile_id=str(loc_data.get("navigation_profile_id") or world_zone.get("navigation_profile_id") or ""),
            buildable_kind=loc_data.get("buildable_kind"),
            landmark_profile=loc_data.get("landmark_profile") or world_zone.get("landmark_profile"),
            movement_profile=loc_data.get("movement_profile") if isinstance(loc_data.get("movement_profile"), dict) else {},
            world_zone=world_zone,
        )
        if dto.world_theme:
            await self._integrator.set_world_theme(char_id, dto.world_theme.model_dump(mode="json"))
        return dto

    def _resolve_background_url(self, loc_data: dict[str, Any]) -> str | None:
        """
        Dynamically resolves a background image path if one is missing from static data.
        Resolution order:
        1. Explicit background_url in loc_data
        2. Mapping by environment tags (most specific, e.g., tavern, forge)
        3. Mapping by terrain type (node level)
        4. Mapping by biome ID (zone level)
        """
        explicit_url = loc_data.get("background_url")
        if explicit_url:
            return explicit_url

        # 1. Environment Tags (Special points of interest)
        tags = loc_data.get("tags") or []
        tag_fallback = {
            "tavern": "tavern_refuge_exterior_01.webp",
            "market": "market_ruins_01.webp",
            "forge": "ancient_forge_01.webp",
            "shrine": "broken_shrine_01.webp",
            "shadow_quarter": "shadow_quarter_01.webp",
            "bastion": "inner_wall_bastion_01.webp",
            "hub_district": "ancient_pavement_hub_01.webp",
            "gate": "city_gate_outer_01.webp",
        }
        for tag in tags:
            if tag in tag_fallback:
                return f"/static/images/exploration/terrain/{tag_fallback[tag]}"

        # 2. Terrain Type (General node appearance)
        terrain = loc_data.get("terrain")
        terrain_fallback = {
            "ancient_pavement": "ancient_pavement_hub_01.webp",
            "ruin_road_main": "ruin_road_main_01.webp",
            "city_ruins": "city_ruins_collapsed_district_01.webp",
            "ruined_foundation": "ruined_foundation_01.webp",
            "city_gate_outer": "city_gate_outer_01.webp",
            "outer_monolith_wall_walk": "outer_monolith_wall_walk_01.webp",
        }
        if terrain in terrain_fallback:
            return f"/static/images/exploration/terrain/{terrain_fallback[terrain]}"

        # 3. Biome ID (Regional default)
        world_zone = loc_data.get("world_zone") or {}
        biome_id = world_zone.get("biome_id")
        biome_fallback = {
            "city_ruins": "city_ruins_collapsed_district_01.webp",
            "hub_district": "ancient_pavement_hub_01.webp",
        }
        if biome_id in biome_fallback:
            return f"/static/images/exploration/terrain/{biome_fallback[biome_id]}"

        # 4. Universal Default (Generic ruins for now)
        return "/static/images/exploration/terrain/city_ruins_collapsed_district_01.webp"

    async def attach_navigation_snapshot(
        self,
        char_id: int,
        loc_id: str,
        loc_data: dict[str, Any],
        payload: Any,
    ) -> Any:
        navigation = await self.build_navigation(char_id, loc_id, loc_data)
        metadata = dict(getattr(payload, "metadata", {}) or {})
        metadata["navigation"] = navigation.model_dump(mode="json")
        return payload.model_copy(update={"metadata": metadata})

    @staticmethod
    def _resolve_target(
        exits: dict[str, Any],
        *,
        direction: str | None,
        target_id: str | None,
    ) -> str | None:
        if target_id and (f"nav:{target_id}" in exits or target_id in exits):
            return target_id
        if direction and (f"nav:{direction}" in exits or direction in exits):
            return direction
        return None

    @staticmethod
    def _safe_threat(value: object) -> float:
        try:
            return max(0.0, min(1.0, float(cast("Any", value))))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _build_navigation_actions(
        loc_id: str,
        exits: dict[str, Any],
        flags: dict[str, Any],
        anchor_influence: dict[str, Any],
    ) -> NavigationActionsDTO:
        if hasattr(NavigationEngine, "build_actions"):
            return NavigationEngine.build_actions(loc_id, exits, flags, anchor_influence)
        return NavigationActionsDTO()
