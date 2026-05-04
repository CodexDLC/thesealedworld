# src/backend/domains/internal_systems/world/services/world_service.py
"""
Бизнес-логика домена World.
Загрузка активных локаций из PostgreSQL в Redis.
"""

from typing import Any

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.postgres.models import WorldGrid
from backend.database.postgres.repositories import get_world_repo
from backend.domains.internal_systems.world.services.world_session_service import WorldSessionService


class WorldService:
    """
    Сервис мира.
    Загружает активные локации из SQL в Redis кэш.
    """

    def __init__(self, session_service: WorldSessionService, db_session: AsyncSession):
        self._session = session_service
        self._db_session = db_session

    # =========================================================================
    # MAIN: Load World Cache
    # =========================================================================

    async def init_world_cache(self) -> int:
        """
        Читает все активные клетки из PostgreSQL и загружает в Redis.

        Returns:
            Количество загруженных локаций
        """
        log.info("WorldService | event=start_loading")

        repo = get_world_repo(self._db_session)

        try:
            active_nodes = await repo.get_active_nodes()
        except (OSError, RuntimeError) as e:
            log.exception(f"WorldService | status=failed error='{e}'")
            return 0

        # Карта для расчёта выходов
        node_map: dict[str, WorldGrid] = {f"{node.x}_{node.y}": node for node in active_nodes}

        count = 0
        for node in active_nodes:
            loc_id = f"{node.x}_{node.y}"

            # Расчёт выходов
            exits_data = self._calculate_exits(node, node_map)

            content: dict[str, Any] = node.content or {}
            flags: dict[str, Any] = node.flags or {}

            # Сервис (берём первый из списка)
            service_val = ""
            if node.services and isinstance(node.services, list) and len(node.services) > 0:
                service_val = node.services[0]

            # Запись в Redis через SessionService
            await self._session.write_location(
                loc_id,
                {
                    "name": content.get("title", f"Узел {loc_id}"),
                    "description": content.get("description", "..."),
                    "exits": exits_data,
                    "tags": content.get("environment_tags", []),
                    "service": service_val,
                    "flags": flags,
                    "zone_id": str(node.zone_id),
                    "terrain": str(node.terrain_type),
                },
            )
            count += 1

        log.info(f"WorldService | status=finished loaded_count={count}")
        return count

    # =========================================================================
    # Location Operations
    # =========================================================================

    async def get_location(self, loc_id: str) -> dict[str, Any] | None:
        """
        Получает данные локации.
        """
        return await self._session.get_location(loc_id)

    async def register_battle(self, loc_id: str, battle_id: str, description: str) -> None:
        """
        Регистрирует бой в локации.
        """
        await self._session.add_battle_to_location(loc_id, battle_id, description)
        log.debug(f"WorldService | battle_registered loc={loc_id} battle={battle_id}")

    async def unregister_battle(self, loc_id: str, battle_id: str) -> None:
        """
        Удаляет бой из локации.
        """
        await self._session.remove_battle_from_location(loc_id, battle_id)
        log.debug(f"WorldService | battle_unregistered loc={loc_id} battle={battle_id}")

    # =========================================================================
    # HELPERS: Exits Calculation
    # =========================================================================

    def _calculate_exits(self, node: WorldGrid, node_map: dict[str, WorldGrid]) -> dict[str, Any]:
        """
        Рассчитывает доступные выходы для локации.
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

        # А. СЕРВИСЫ
        if node.services and isinstance(node.services, list):
            for svc in node.services:
                key = f"svc:{svc}"
                btn_name, desc_room = self._get_service_labels(svc)
                exits[key] = {
                    "desc_next_room": desc_room,
                    "time_duration": 0.0,
                    "text_button": btn_name,
                    "type": "service",
                }

        # Б. НАВИГАЦИЯ
        ru_dirs = {"north": "Север", "south": "Юг", "west": "Запад", "east": "Восток"}

        for dir_name, (dx, dy) in directions.items():
            if dir_name in restricted:
                continue

            nx, ny = node.x + dx, node.y + dy
            neighbor_id = f"{nx}_{ny}"
            neighbor = node_map.get(neighbor_id)

            if not neighbor or not neighbor.is_active:
                continue

            neighbor_flags = neighbor.flags if isinstance(neighbor.flags, dict) else {}
            neighbor_has_road = neighbor_flags.get("has_road", False)

            # Изоляция регионов
            my_region = self._get_region_from_zone(str(node.zone_id))
            neighbor_region = self._get_region_from_zone(str(neighbor.zone_id))

            if my_region != neighbor_region and not (my_has_road and neighbor_has_road):
                continue

            content = neighbor.content or {}
            title = content.get("title") or f"Путь в {nx}:{ny}"
            time_duration = 2.0 if (my_has_road and neighbor_has_road) else 4.0

            exits[f"nav:{neighbor_id}"] = {
                "desc_next_room": title,
                "time_duration": time_duration,
                "text_button": f"На {ru_dirs.get(dir_name, dir_name)}",
                "type": "move",
                "direction": dir_name,
            }

        return exits

    def _get_service_labels(self, svc: str) -> tuple[str, str]:
        """
        Возвращает (text_button, desc_next_room) для сервиса.
        """
        if "portal" in svc:
            return "К Порталу", "Войти в Портал"
        if "tavern" in svc:
            return "В Таверну", "Войти в Таверну"
        if "arena" in svc:
            return "На Арену", "Выйти на Арену"
        return "Войти", "Вход в Сервис"

    def _get_region_from_zone(self, zone_id: str) -> str:
        """
        Извлекает ID региона из zone_id.
        """
        parts = zone_id.split("_")
        return parts[0] if parts else zone_id
