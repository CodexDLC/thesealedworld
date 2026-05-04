from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.infrastructure.world.models import WorldGrid


class WorldNavigationService:
    DIRECTIONS = {
        "north": (0, -1),
        "south": (0, 1),
        "west": (-1, 0),
        "east": (1, 0),
    }
    RU_DIRECTIONS = {"north": "Север", "south": "Юг", "west": "Запад", "east": "Восток"}

    def calculate_exits(self, node: WorldGrid, node_map: dict[str, WorldGrid]) -> dict[str, Any]:
        exits: dict[str, Any] = {}
        flags = node.flags if isinstance(node.flags, dict) else {}
        has_road = bool(flags.get("has_road", False))
        restricted = set(flags.get("restricted_exits", []))

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
            if direction in restricted:
                continue

            nx = node.x + dx
            ny = node.y + dy
            neighbor_id = f"{nx}_{ny}"
            neighbor = node_map.get(neighbor_id)
            if neighbor is None or not neighbor.is_active:
                continue

            neighbor_flags = neighbor.flags if isinstance(neighbor.flags, dict) else {}
            neighbor_has_road = bool(neighbor_flags.get("has_road", False))
            if self._region_from_zone(str(node.zone_id)) != self._region_from_zone(str(neighbor.zone_id)) and not (
                has_road and neighbor_has_road
            ):
                continue

            content = neighbor.content or {}
            title = content.get("title") or f"Путь в {nx}:{ny}"
            exits[f"nav:{neighbor_id}"] = {
                "desc_next_room": title,
                "time_duration": 2.0 if has_road and neighbor_has_road else 4.0,
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
