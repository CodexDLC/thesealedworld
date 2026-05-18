from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from src.backend.features.exploration.dto.config import ExplorationConfig
from src.backend.features.exploration.dto.result import MoveResolution
from src.backend.features.exploration.resources.service_registry import get_service_entry
from src.backend.features.exploration.runtime.city_map import build_city_map_payload
from src.backend.features.exploration.runtime.navigation import NavigationEngine
from src.shared.schemas.exploration import (
    AlertHudDTO,
    ExplorationHudDTO,
    ExplorationLocalMapDTO,
    ExplorationMapCellDTO,
    ExplorationMapEdgeDTO,
    NavigationActionsDTO,
    WorldNavigationDTO,
)
from src.shared.schemas.world_theme import WorldThemeDTO

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.backend.features.exploration.integrations.system_integrator import ExplorationSystemIntegrator


class ExplorationNavigationService:
    """Owns movement validation and navigation payload assembly."""

    MAP_DIRECTIONS: dict[str, tuple[int, int]] = {
        "north": (0, -1),
        "south": (0, 1),
        "west": (-1, 0),
        "east": (1, 0),
    }
    OPPOSITE_DIRECTIONS: dict[str, str] = {
        "north": "south",
        "south": "north",
        "west": "east",
        "east": "west",
    }

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

    async def build_local_map(self, char_id: int, *, radius: int = 2) -> ExplorationLocalMapDTO:
        radius = max(1, min(int(radius), 4))
        current_loc_id = await self.current_loc_id(char_id)
        current_x, current_y = NavigationEngine._parse_coords(current_loc_id)
        if current_x is None or current_y is None:
            current_x, current_y = 0, 0

        rows: list[list[ExplorationMapCellDTO]] = []
        for y in range(current_y - radius, current_y + radius + 1):
            row: list[ExplorationMapCellDTO] = []
            for x in range(current_x - radius, current_x + radius + 1):
                loc_id = f"{x}_{y}"
                loc_data = await self.location_data(loc_id)
                row.append(
                    await self._build_map_cell(
                        char_id=char_id,
                        current_loc_id=current_loc_id,
                        current_x=current_x,
                        current_y=current_y,
                        loc_id=loc_id,
                        x=x,
                        y=y,
                        loc_data=loc_data,
                    )
                )
            rows.append(row)

        rows = self._attach_render_edges(rows, current_x=current_x, current_y=current_y)
        return ExplorationLocalMapDTO(
            char_id=char_id,
            current_loc_id=current_loc_id,
            radius=radius,
            size=radius * 2 + 1,
            rows=rows,
        )

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
        city_map = build_city_map_payload(loc_id, loc_data)
        dto = WorldNavigationDTO(
            loc_id=loc_id,
            title=loc_data.get("name", "Unknown"),
            description=loc_data.get("description", "..."),
            background_url=None if city_map else self._explicit_background_url(loc_data),
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
            navigation_profile_id=str(
                loc_data.get("navigation_profile_id") or world_zone.get("navigation_profile_id") or ""
            ),
            buildable_kind=loc_data.get("buildable_kind"),
            landmark_profile=loc_data.get("landmark_profile") or world_zone.get("landmark_profile"),
            movement_profile=_safe_dict(loc_data.get("movement_profile")),
            world_zone=world_zone,
            city_map=city_map,
        )
        if dto.world_theme:
            await self._integrator.set_world_theme(char_id, dto.world_theme.model_dump(mode="json"))
        return dto

    @staticmethod
    def _explicit_background_url(loc_data: dict[str, Any]) -> str | None:
        explicit_url = loc_data.get("background_url")
        return explicit_url if isinstance(explicit_url, str) and explicit_url else None

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

    async def _build_map_cell(
        self,
        *,
        char_id: int,
        current_loc_id: str,
        current_x: int,
        current_y: int,
        loc_id: str,
        x: int,
        y: int,
        loc_data: dict[str, Any],
    ) -> ExplorationMapCellDTO:
        if not loc_data:
            return ExplorationMapCellDTO(
                loc_id=loc_id,
                x=x,
                y=y,
                dx=x - current_x,
                dy=y - current_y,
                is_current=loc_id == current_loc_id,
                is_known=False,
                edges=self._unknown_edges(),
                tooltip={"loc_id": loc_id, "status": "NO_DATA"},
            )

        flags = loc_data.get("flags", {})
        flags = flags if isinstance(flags, dict) else {}
        anchor_influence = loc_data.get("anchor_influence", {})
        anchor_influence = anchor_influence if isinstance(anchor_influence, dict) else {}
        services = loc_data.get("services", [])
        services = services if isinstance(services, list) else []
        service_labels = _service_labels(services)
        tags = loc_data.get("tags", [])
        tags = tags if isinstance(tags, list) else []
        threat = self._safe_threat(anchor_influence.get("threat", flags.get("threat", 0.0)))
        threat_tier = _safe_int(flags.get("threat_tier"))
        is_safe_zone = NavigationEngine.is_safe_context(flags, anchor_influence)
        system_connect = bool(flags.get("system_connect") or flags.get("is_safe_zone", False))
        players_count = await self._players_count(loc_id, char_id=char_id)
        battles = await self._integrator.get_battles(loc_id)
        corpse_count = await self._corpse_count(loc_id)
        title = _safe_str(loc_data.get("name")) or _safe_str(loc_data.get("title"))
        description = _safe_str(loc_data.get("description"))

        tooltip = {
            "loc_id": loc_id,
            "title": title or "NO_DATA",
            "description": description or "NO_DATA",
            "x": x,
            "y": y,
            "zone_id": _safe_str(loc_data.get("zone_id")),
            "terrain": _safe_str(loc_data.get("terrain")),
            "node_type": _safe_str(loc_data.get("node_type")),
            "is_safe_zone": is_safe_zone,
            "system_connect": system_connect,
            "threat": threat,
            "threat_tier": threat_tier,
            "players_count": players_count,
            "battles_count": len(battles),
            "corpse_count": corpse_count,
            "services_count": len(services),
            "service_labels": service_labels,
            "tags": tags,
            "background_available": bool(loc_data.get("background_url")),
        }

        return ExplorationMapCellDTO(
            loc_id=loc_id,
            x=x,
            y=y,
            dx=x - current_x,
            dy=y - current_y,
            is_current=loc_id == current_loc_id,
            is_known=True,
            title=title,
            description=description,
            zone_id=_safe_str(loc_data.get("zone_id")),
            terrain=_safe_str(loc_data.get("terrain")),
            node_type=_safe_str(loc_data.get("node_type")),
            is_safe_zone=is_safe_zone,
            system_connect=system_connect,
            threat=threat,
            threat_tier=threat_tier,
            dominant_anchor=_safe_str(anchor_influence.get("dominant_anchor")) or None,
            tags=[str(tag) for tag in tags],
            service_count=len(services),
            service_labels=service_labels,
            players_count=players_count,
            battles_count=len(battles),
            corpse_count=corpse_count,
            background_available=bool(loc_data.get("background_url")),
            edges=self._edge_map(loc_id, loc_data),
            tooltip=tooltip,
        )

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

    async def _players_count(self, loc_id: str, *, char_id: int) -> int:
        try:
            return await self._integrator.get_players_count(loc_id, exclude_char_id=char_id)
        except TypeError:
            return await self._integrator.get_players_count(loc_id)

    async def _corpse_count(self, loc_id: str) -> int | None:
        getter = getattr(self._integrator, "get_corpse_count", None)
        if getter is None:
            return None
        return await getter(loc_id)

    @classmethod
    def _unknown_edges(cls) -> dict[str, ExplorationMapEdgeDTO]:
        return {
            direction: ExplorationMapEdgeDTO(direction=cast("Any", direction), state="unknown")
            for direction in cls.MAP_DIRECTIONS
        }

    @classmethod
    def _edge_map(cls, loc_id: str, loc_data: dict[str, Any]) -> dict[str, ExplorationMapEdgeDTO]:
        x, y = NavigationEngine._parse_coords(loc_id)
        if x is None or y is None:
            return cls._unknown_edges()

        movement = loc_data.get("movement_profile", {})
        movement = movement if isinstance(movement, dict) else {}
        blocked = movement.get("blocked_exits", [])
        blocked = set(blocked) if isinstance(blocked, list) else set()
        gated = movement.get("gated_exits", {})
        gated = gated if isinstance(gated, dict) else {}
        exits = loc_data.get("exits", {})
        exits = exits if isinstance(exits, dict) else {}

        edges: dict[str, ExplorationMapEdgeDTO] = {}
        for direction, (dx, dy) in cls.MAP_DIRECTIONS.items():
            target_loc_id = f"{x + dx}_{y + dy}"
            exit_data = _nav_exit(exits, target_loc_id)
            gate_data = gated.get(direction)
            if isinstance(gate_data, dict) and gate_data.get("state") not in {None, "open"}:
                state = "locked"
            elif direction in blocked:
                state = "blocked"
            elif exit_data is not None:
                state = "open"
            else:
                state = "blocked"

            edges[direction] = ExplorationMapEdgeDTO(
                direction=cast("Any", direction),
                state=cast("Any", state),
                target_loc_id=target_loc_id if state == "open" else None,
                label=_safe_str((exit_data or {}).get("desc_next_room")) if exit_data else None,
                travel_time=_safe_float((exit_data or {}).get("time_duration")) if exit_data else None,
                tooltip=NavigationEngine._move_tooltip(exit_data) if exit_data else None,
            )
        return edges

    @classmethod
    def _attach_render_edges(
        cls,
        rows: list[list[ExplorationMapCellDTO]],
        *,
        current_x: int,
        current_y: int,
    ) -> list[list[ExplorationMapCellDTO]]:
        cells = {(cell.x, cell.y): cell for row in rows for cell in row}
        render_edges: dict[tuple[int, int], dict[str, ExplorationMapEdgeDTO]] = {coords: {} for coords in cells}
        seen_pairs: set[tuple[tuple[int, int], tuple[int, int]]] = set()

        for (x, y), cell in cells.items():
            for direction, edge in cell.edges.items():
                if edge.state not in {"blocked", "locked"}:
                    continue
                dx, dy = cls.MAP_DIRECTIONS.get(direction, (0, 0))
                target = (x + dx, y + dy)
                pair = tuple(sorted(((x, y), target)))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                owner = cls._render_edge_owner((x, y), target, current_x=current_x, current_y=current_y)
                if owner == target and target in cells:
                    render_direction = cls.OPPOSITE_DIRECTIONS[direction]
                else:
                    owner = (x, y)
                    render_direction = direction

                if owner not in render_edges:
                    continue
                render_edges[owner][render_direction] = edge.model_copy(
                    update={"direction": cast("Any", render_direction)}
                )

        return [
            [cell.model_copy(update={"render_edges": render_edges[(cell.x, cell.y)]}) for cell in row] for row in rows
        ]

    @staticmethod
    def _render_edge_owner(
        source: tuple[int, int],
        target: tuple[int, int],
        *,
        current_x: int,
        current_y: int,
    ) -> tuple[int, int]:
        source_distance = abs(source[0] - current_x) + abs(source[1] - current_y)
        target_distance = abs(target[0] - current_x) + abs(target[1] - current_y)
        if target_distance > source_distance:
            return target
        if source_distance > target_distance:
            return source
        return max(source, target, key=lambda coords: (coords[1], coords[0]))

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


def _nav_exit(exits: dict[str, Any], target_loc_id: str) -> dict[str, Any] | None:
    raw = exits.get(f"nav:{target_loc_id}") or exits.get(target_loc_id)
    return raw if isinstance(raw, dict) else None


def _safe_str(value: object) -> str:
    return value if isinstance(value, str) else ""


def _safe_float(value: object) -> float | None:
    try:
        return float(cast("Any", value))
    except (TypeError, ValueError):
        return None


def _safe_int(value: object) -> int | None:
    try:
        return int(cast("Any", value))
    except (TypeError, ValueError):
        return None


def _safe_dict(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _service_labels(services: list[Any]) -> list[str]:
    labels: list[str] = []
    for raw_service_id in services:
        service_id = str(raw_service_id)
        entry = get_service_entry(service_id)
        labels.append(entry.label if entry else service_id.removeprefix("svc_").replace("_", " ").title())
    return labels
