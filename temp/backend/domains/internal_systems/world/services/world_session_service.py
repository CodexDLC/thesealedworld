# backend/domains/internal_systems/world/services/world_session_service.py
"""
Data Access Layer для домена World.
Инкапсулирует работу с Redis через WorldManager.
"""

import json
from typing import Any

from loguru import logger as log

from src.backend.database.redis.manager.world_manager import WorldManager


class WorldSessionService:
    """
    Сервис сессии мира.
    Предоставляет методы для записи/чтения данных локаций в Redis.
    """

    def __init__(self, world_manager: WorldManager):
        self._world_mgr = world_manager

    # =========================================================================
    # WRITING: Location Data
    # =========================================================================

    async def write_location(self, loc_id: str, data: dict[str, Any]) -> None:
        """
        Записывает метаданные локации в Redis.

        Args:
            loc_id: ID локации (формат "X_Y")
            data: Словарь с полями: name, description, exits, flags, tags, service, zone_id, terrain
        """
        # Сериализуем JSON-поля
        redis_data = {
            "name": data.get("name", f"Локация {loc_id}"),
            "description": data.get("description", "..."),
            "exits": json.dumps(data.get("exits", {}), ensure_ascii=False),
            "flags": json.dumps(data.get("flags", {}), ensure_ascii=False),
            "tags": json.dumps(data.get("tags", []), ensure_ascii=False),
            "service": data.get("service", ""),
            "zone_id": str(data.get("zone_id", "")),
            "terrain": str(data.get("terrain", "wasteland")),
        }

        await self._world_mgr.write_location_meta(loc_id, redis_data)

    async def write_location_batch(self, locations: list[dict[str, Any]]) -> int:
        """
        Пакетная запись локаций.

        Args:
            locations: Список локаций с полем 'loc_id'

        Returns:
            Количество записанных локаций
        """
        count = 0
        for loc_data in locations:
            loc_id = loc_data.get("loc_id")
            if not loc_id:
                continue
            await self.write_location(loc_id, loc_data)
            count += 1
        return count

    # =========================================================================
    # READING: Location Data
    # =========================================================================

    async def get_location(self, loc_id: str) -> dict[str, Any] | None:
        """
        Получает данные локации из Redis.
        """
        raw_data = await self._world_mgr.get_location_meta(loc_id)
        if not raw_data:
            return None
        return self._parse_location_data(loc_id, raw_data)

    async def location_exists(self, loc_id: str) -> bool:
        """
        Проверяет существование локации.
        """
        return await self._world_mgr.location_meta_exists(loc_id)

    # =========================================================================
    # READING: Players & Battles
    # =========================================================================

    async def get_players_in_location(self, loc_id: str) -> set[str]:
        """
        Получает множество char_id игроков в локации.
        """
        return await self._world_mgr.get_players_in_location(loc_id)

    async def get_battles_in_location(self, loc_id: str) -> dict[str, str]:
        """
        Получает словарь активных боев {battle_id: description}.
        """
        return await self._world_mgr.get_battles_in_location(loc_id) or {}

    # =========================================================================
    # WRITING: Players & Battles
    # =========================================================================

    async def add_player_to_location(self, loc_id: str, char_id: int) -> None:
        """
        Добавляет игрока в локацию.
        """
        await self._world_mgr.add_player_to_location(loc_id, char_id)

    async def remove_player_from_location(self, loc_id: str, char_id: int) -> None:
        """
        Удаляет игрока из локации.
        """
        await self._world_mgr.remove_player_from_location(loc_id, char_id)

    async def add_battle_to_location(self, loc_id: str, battle_id: str, description: str) -> None:
        """
        Добавляет бой в локацию.
        """
        await self._world_mgr.add_battle_to_location(loc_id, battle_id, description)

    async def remove_battle_from_location(self, loc_id: str, battle_id: str) -> None:
        """
        Удаляет бой из локации.
        """
        await self._world_mgr.remove_battle_from_location(loc_id, battle_id)

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _parse_location_data(self, loc_id: str, raw_data: dict[str, str]) -> dict[str, Any] | None:
        """
        Парсит JSON-поля из сырых данных Redis.
        """
        try:
            exits = json.loads(raw_data.get("exits", "{}"))
            flags = json.loads(raw_data.get("flags", "{}"))
            tags = json.loads(raw_data.get("tags", "[]"))

            return {
                "loc_id": loc_id,
                "name": raw_data.get("name", "Неизвестная локация"),
                "description": raw_data.get("description", "..."),
                "exits": exits,
                "flags": flags,
                "tags": tags,
                "service": raw_data.get("service"),
                "zone_id": raw_data.get("zone_id"),
                "terrain": raw_data.get("terrain", "wasteland"),
            }
        except json.JSONDecodeError as e:
            log.error(f"WorldSessionService | json_parse_error loc_id={loc_id} error={e}")
            return None
