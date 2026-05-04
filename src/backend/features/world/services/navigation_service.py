from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.infrastructure.world.models import WorldGrid


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

    def calculate_exits(self, node: WorldGrid, node_map: dict[str, WorldGrid]) -> dict[str, Any]:
        exits: dict[str, Any] = {}
        flags = node.flags if isinstance(node.flags, dict) else {}
        has_road = bool(flags.get("has_road", False))
        blocked = self._blocked_exits(flags)
        gated = flags.get("gated_exits", {})
        gated = gated if isinstance(gated, dict) else {}

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

            neighbor_flags = neighbor.flags if isinstance(neighbor.flags, dict) else {}
            if neighbor_flags.get("is_passable") is False:
                continue
            reverse_direction = self.OPPOSITE_DIRECTIONS[direction]
            if reverse_direction in self._blocked_exits(neighbor_flags):
                continue
            neighbor_gated = neighbor_flags.get("gated_exits", {})
            neighbor_gated = neighbor_gated if isinstance(neighbor_gated, dict) else {}
            if self._is_locked_gate(neighbor_gated.get(reverse_direction)):
                continue

            neighbor_has_road = bool(neighbor_flags.get("has_road", False))
            if self._region_from_zone(str(node.zone_id)) != self._region_from_zone(str(neighbor.zone_id)) and not (
                has_road and neighbor_has_road
            ):
                continue

            content = neighbor.content or {}
            title = content.get("title") or f"Путь в {nx}:{ny}"
            exits[f"nav:{neighbor_id}"] = {
                "desc_next_room": title,
                "time_duration": self._travel_time(flags, neighbor_flags),
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
    def _blocked_exits(flags: dict[str, Any]) -> set[str]:
        blocked = flags.get("blocked_exits", flags.get("restricted_exits", []))
        return set(blocked) if isinstance(blocked, list) else set()

    @staticmethod
    def _is_locked_gate(gate_data: Any) -> bool:
        return isinstance(gate_data, dict) and gate_data.get("state") == "locked"

    def _travel_time(self, flags: dict[str, Any], neighbor_flags: dict[str, Any]) -> float:
        if flags.get("has_road") and neighbor_flags.get("has_road"):
            return self.ROAD_STEP_SECONDS

        current_cost = self._travel_cost(flags)
        neighbor_cost = self._travel_cost(neighbor_flags)
        return round(self.BASE_STEP_SECONDS * max(current_cost, neighbor_cost), 2)

    @staticmethod
    def _travel_cost(flags: dict[str, Any]) -> float:
        value = flags.get("travel_cost", 1.0)
        try:
            return max(float(value), 1.0)
        except (TypeError, ValueError):
            return 1.0
