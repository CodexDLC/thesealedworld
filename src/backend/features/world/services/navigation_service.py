from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Mapping


class WorldNavigationNode(Protocol):
    x: int
    y: int
    zone_id: str
    biome_id: str | None
    node_type: str
    terrain_type: str
    navigation_profile_id: str
    buildable_kind: str | None
    landmark_profile: str | None
    movement_profile: dict[str, Any]
    background_key: str | None
    background_pool_key: str | None
    visual_overrides: dict[str, Any]
    services: list[str]
    content: dict[str, Any] | None
    flags: dict[str, Any]
    is_active: bool


class WorldNavigationService:
    BASE_STEP_SECONDS = 4.0
    ROAD_STEP_SECONDS = 2.0
    DIRECTIONS = {
        "north": (0, -1),
        "south": (0, 1),
        "west": (-1, 0),
        "east": (1, 0),
    }
    RU_DIRECTIONS = {"north": "Север", "south": "Юг", "west": "Запад", "east": "Восток"}
    OPPOSITE_DIRECTIONS = {"north": "south", "south": "north", "west": "east", "east": "west"}

    def calculate_exits(self, node: WorldNavigationNode, node_map: Mapping[str, WorldNavigationNode]) -> dict[str, Any]:
        exits: dict[str, Any] = {}
        movement = self._movement_profile(node)
        if movement.get("is_passable") is False:
            return exits

        has_road = bool(movement.get("has_road", False))
        blocked = self._blocked_exits(movement)
        gated = self._gated_exits(movement)

        if isinstance(node.services, list):
            for service in node.services:
                button, description = self._service_labels(service)
                exits[f"svc:{service}"] = {
                    "desc_next_room": description,
                    "time_duration": 0.0,
                    "text_button": button,
                    "type": "service",
                }

        for direction, (dx, dy) in self.DIRECTIONS.items():
            if direction in blocked:
                continue
            if self._is_locked_gate(gated.get(direction)):
                continue

            nx = node.x + dx
            ny = node.y + dy
            neighbor_id = f"{nx}_{ny}"
            neighbor = node_map.get(neighbor_id)
            if neighbor is None or not neighbor.is_active:
                continue

            neighbor_movement = self._movement_profile(neighbor)
            if neighbor_movement.get("is_passable") is False:
                continue
            reverse_direction = self.OPPOSITE_DIRECTIONS[direction]
            if reverse_direction in self._blocked_exits(neighbor_movement):
                continue
            neighbor_gated = self._gated_exits(neighbor_movement)
            if self._is_locked_gate(neighbor_gated.get(reverse_direction)):
                continue

            neighbor_has_road = bool(neighbor_movement.get("has_road", False))
            if self._region_from_zone(str(node.zone_id)) != self._region_from_zone(str(neighbor.zone_id)) and not (
                has_road and neighbor_has_road
            ):
                continue

            content = neighbor.content or {}
            title = content.get("title") or f"Путь в {nx}:{ny}"
            exits[f"nav:{neighbor_id}"] = {
                "desc_next_room": title,
                "time_duration": self._travel_time(movement, neighbor_movement),
                "text_button": f"На {self.RU_DIRECTIONS.get(direction, direction)}",
                "type": "move",
                "direction": direction,
            }

        return exits

    @staticmethod
    def _service_labels(service: str) -> tuple[str, str]:
        if "portal" in service:
            return "К Порталу", "Войти в Портал"
        if "tavern" in service:
            return "В Таверну", "Войти в Таверну"
        if "arena" in service:
            return "На Арену", "Выйти на Арену"
        return "Войти", "Вход в Сервис"

    @staticmethod
    def _region_from_zone(zone_id: str) -> str:
        parts = zone_id.split("_")
        return parts[0] if parts else zone_id

    @staticmethod
    def _movement_profile(node: WorldNavigationNode) -> dict[str, Any]:
        movement = node.movement_profile
        return movement if isinstance(movement, dict) else {}

    @staticmethod
    def _blocked_exits(movement: dict[str, Any]) -> set[str]:
        blocked = movement.get("blocked_exits", [])
        return set(blocked) if isinstance(blocked, list) else set()

    @staticmethod
    def _gated_exits(movement: dict[str, Any]) -> dict[str, Any]:
        gated = movement.get("gated_exits", {})
        return gated if isinstance(gated, dict) else {}

    @staticmethod
    def _is_locked_gate(gate_data: Any) -> bool:
        return isinstance(gate_data, dict) and gate_data.get("state") == "locked"

    def _travel_time(self, movement: dict[str, Any], neighbor_movement: dict[str, Any]) -> float:
        if movement.get("has_road") and neighbor_movement.get("has_road"):
            return self.ROAD_STEP_SECONDS

        current_cost = self._travel_cost(movement)
        neighbor_cost = self._travel_cost(neighbor_movement)
        return round(self.BASE_STEP_SECONDS * max(current_cost, neighbor_cost), 2)

    @staticmethod
    def _travel_cost(movement: dict[str, Any]) -> float:
        value = movement.get("travel_cost", 1.0)
        try:
            return max(float(value), 1.0)
        except (TypeError, ValueError):
            return 1.0
