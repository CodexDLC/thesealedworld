import json
from typing import Any

from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError

from src.backend.core.database import get_session_context
from src.backend.database.postgres.models import WorldGrid
from src.backend.database.postgres.repositories import get_world_repo


class WorldLoaderService:
    """
    Сервис загрузки активной части мира (Active Grid) из SQL в кэш Redis.
    Архитектура: Iterator -> WorldManager.write_location_meta
    """

    def __init__(self, world_manager):
        self.world_manager = world_manager
        log.debug("WorldLoaderService | status=initialized")

    async def init_world_cache(self) -> int:
        """
        Читает все активные клетки (nodes) из SQL, рассчитывает выходы и загружает их в Redis.
        """
        log.info("WorldLoaderService | event=start_loading_active_nodes")

        async with get_session_context() as session:
            repo = get_world_repo(session)

            try:
                active_nodes = await repo.get_active_nodes()
            except SQLAlchemyError as e:
                log.exception(f"WorldLoaderService | status=failed reason='SQL fetch error' error='{e}'")
                return 0

            # Создаем карту для быстрого поиска соседей
            node_map: dict[str, WorldGrid] = {f"{node.x}_{node.y}": node for node in active_nodes}

            count = 0
            for node in active_nodes:
                loc_id = f"{node.x}_{node.y}"

                # 1. Расчет выходов
                exits_data = self._calculate_exits_for_node(node, node_map)

                content_data: dict[str, Any] = node.content or {}
                flags_data: dict[str, Any] = node.flags or {}

                # 2. Обработка сервисов (Адаптация под List в новой БД)
                # Если services это список ["svc_portal"], берем первый.
                service_val = ""
                if node.services and isinstance(node.services, list) and len(node.services) > 0:
                    service_val = node.services[0]

                # 3. Подготовка данных для Redis
                redis_data = {
                    "name": content_data.get("title", f"Узел {loc_id}"),
                    "description": content_data.get("description", "..."),
                    "exits": json.dumps(exits_data, ensure_ascii=False),  # Важно: False для русского языка
                    "tags": json.dumps(content_data.get("environment_tags", []), ensure_ascii=False),
                    "service": service_val,
                    "flags": json.dumps(flags_data, ensure_ascii=False),
                    "zone_id": str(node.zone_id),
                    "terrain": str(node.terrain_type),
                }

                # 4. Вызов твоего менеджера (как было раньше)
                await self.world_manager.write_location_meta(loc_id, redis_data)
                count += 1

            log.info(f"WorldLoaderService | status=finished loaded_count={count}")
            return count

    def _get_region_id_from_zone_id(self, zone_id: str) -> str:
        """
        Извлекает ID региона из ID зоны.
        """
        parts = zone_id.split("_")
        if len(parts) > 1:
            return parts[0]
        return zone_id

    def _calculate_exits_for_node(self, node: WorldGrid, node_map: dict[str, WorldGrid]) -> dict[str, Any]:
        """
        Рассчитывает доступные выходы.
        """
        exits = {}
        directions = {
            "north": (0, -1),
            "south": (0, 1),
            "west": (-1, 0),
            "east": (1, 0),
        }

        my_flags = node.flags if isinstance(node.flags, dict) else {}
        my_has_road = my_flags.get("has_road", False)
        restricted = my_flags.get("restricted_exits", [])

        # А. СЕРВИСЫ (Адаптация под список)
        if node.services and isinstance(node.services, list):
            for svc in node.services:
                key = f"svc:{svc}"
                # Логика кнопки
                btn_name = "Войти"
                desc_room = "Вход в Сервис"
                if "portal" in svc:
                    btn_name = "К Порталу"
                    desc_room = "Войти в Портал"
                elif "tavern" in svc:
                    btn_name = "В Таверну"
                    desc_room = "Войти в Таверну"
                elif "arena" in svc:
                    btn_name = "На Арену"
                    desc_room = "Выйти на Арену"

                exits[key] = {
                    "desc_next_room": desc_room,
                    "time_duration": 0.0,
                    "text_button": btn_name,
                    "type": "service",
                }

        # Б. НАВИГАЦИЯ
        for dir_name, (dx, dy) in directions.items():
            if dir_name in restricted:
                continue

            nx, ny = node.x + dx, node.y + dy
            neighbor_id = f"{nx}_{ny}"
            neighbor = node_map.get(neighbor_id)

            if neighbor and neighbor.is_active:
                content = neighbor.content or {}
                title = content.get("title") or f"Путь в {nx}:{ny}"

                neighbor_flags = neighbor.flags if isinstance(neighbor.flags, dict) else {}
                neighbor_has_road = neighbor_flags.get("has_road", False)

                # Логика изоляции регионов
                my_region_id = self._get_region_id_from_zone_id(str(node.zone_id))
                neighbor_region_id = self._get_region_id_from_zone_id(str(neighbor.zone_id))

                is_region_crossing = my_region_id != neighbor_region_id

                if is_region_crossing and not (my_has_road and neighbor_has_road):
                    continue

                time_duration = 2.0 if (my_has_road and neighbor_has_road) else 4.0

                # Перевод направлений для кнопки
                ru_dirs = {"north": "Север", "south": "Юг", "west": "Запад", "east": "Восток"}
                dir_ru = ru_dirs.get(dir_name, dir_name)

                key = f"nav:{neighbor_id}"

                exits[key] = {
                    "desc_next_room": title,
                    "time_duration": time_duration,
                    "text_button": f"На {dir_ru}",
                    "type": "move",
                    "direction": dir_name,
                }

        return exits
