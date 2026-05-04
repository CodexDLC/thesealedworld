# backend/domains/user_features/exploration/services/exploration_session_service.py
"""
Data Access Layer для домена Exploration.
Инкапсулирует работу с Redis через AccountManager и WorldManager.
"""

import json
from typing import Any

from loguru import logger as log

from src.backend.database.redis.manager.account_manager import AccountManager
from src.backend.database.redis.manager.world_manager import WorldManager
from src.backend.domains.user_features.exploration.data.config import ExplorationConfig


class ExplorationSessionService:
    """
    Сервис сессии исследования.
    Предоставляет методы для чтения/записи данных о локациях и позиции игрока.
    """

    def __init__(self, account_manager: AccountManager, world_manager: WorldManager):
        self._account_mgr = account_manager
        self._world_mgr = world_manager

    # =========================================================================
    # READING: Player Location
    # =========================================================================

    async def get_player_location_id(self, char_id: int) -> str:
        """
        Получает текущую локацию игрока.
        Возвращает DEFAULT_SPAWN_POINT если локация не установлена.
        """
        location_data = await self._account_mgr.get_location(char_id)
        if location_data and location_data.get("current"):
            return location_data["current"]
        return ExplorationConfig.DEFAULT_SPAWN_POINT

    async def get_player_prev_location_id(self, char_id: int) -> str | None:
        """
        Получает предыдущую локацию игрока.
        """
        location_data = await self._account_mgr.get_location(char_id)
        if location_data:
            return location_data.get("previous")
        return None

    # =========================================================================
    # READING: Player Skills
    # =========================================================================

    async def get_actor_skill(self, char_id: int, skill_name: str) -> int:
        """
        Получает значение скилла, приведенное к шкале 0-100.
        В базе скилл хранится как float (0.0 - 1.0).
        Пример: 0.4561 -> 45
        """
        # Путь к скиллу в JSON: $.skills.survival
        val = await self._account_mgr.get_account_field(char_id, f"$.skills.{skill_name}")
        try:
            if val is None:
                return 0

            float_val = float(val)

            # Если значение <= 1.0, считаем что это коэффициент (0.45) -> умножаем на 100
            if float_val <= 1.0:
                return int(float_val * 100)

            # Если значение > 1.0, считаем что это уже проценты (45.6) -> просто int
            return int(float_val)

        except (ValueError, TypeError):
            return 0

    # =========================================================================
    # READING: Location Data
    # =========================================================================

    async def get_location_data(self, loc_id: str) -> dict[str, Any] | None:
        """
        Получает полные данные локации из Redis.
        Парсит JSON-поля (exits, flags, tags).

        Returns:
            dict с ключами: name, description, exits, flags, tags, service, zone_id, terrain
            или None если локация не найдена.
        """
        raw_data = await self._world_mgr.get_location_meta(loc_id)
        if not raw_data:
            log.warning(f"ExplorationSession | location_not_found loc_id={loc_id}")
            return None

        return self._parse_location_data(loc_id, raw_data)

    async def get_location_exists(self, loc_id: str) -> bool:
        """
        Проверяет существование локации.
        """
        return await self._world_mgr.location_meta_exists(loc_id)

    async def get_players_in_location(self, loc_id: str) -> set[str]:
        """
        Получает множество char_id игроков в локации.
        """
        return await self._world_mgr.get_players_in_location(loc_id)

    async def get_players_count_in_location(self, loc_id: str, exclude_char_id: int | None = None) -> int:
        """
        Получает количество игроков в локации.
        Опционально исключает указанного игрока из подсчета.
        """
        players = await self.get_players_in_location(loc_id)
        if exclude_char_id is not None:
            players.discard(str(exclude_char_id))
        return len(players)

    async def get_active_battles_count(self, loc_id: str) -> int:
        """
        Получает количество активных боев в локации.
        """
        battles = await self._world_mgr.get_battles_in_location(loc_id)
        return len(battles)

    async def get_battles(self, loc_id: str) -> dict[str, str]:
        """
        Получает словарь активных боев {uuid: description}.
        """
        return await self._world_mgr.get_battles_in_location(loc_id) or {}

    # =========================================================================
    # WRITING: Movement
    # =========================================================================

    async def move_player(self, char_id: int, to_loc_id: str) -> bool:
        """
        Перемещает игрока в новую локацию.
        Автоматически сохраняет текущую локацию как previous.

        1. Получает текущую локацию
        2. Удаляет игрока из старой локации (SET)
        3. Добавляет игрока в новую локацию (SET)
        4. Обновляет account (current -> previous, new -> current)

        Returns:
            True если перемещение успешно.
        """
        # 1. Получаем текущую локацию
        current_loc_id = await self.get_player_location_id(char_id)

        # 2. Проверяем существование целевой локации
        if not await self.get_location_exists(to_loc_id):
            log.warning(f"ExplorationSession | move_failed reason=target_not_found char_id={char_id} to={to_loc_id}")
            return False

        # 3. Обновляем SET'ы игроков в локациях
        if current_loc_id and current_loc_id != ExplorationConfig.DEFAULT_SPAWN_POINT:
            await self._world_mgr.remove_player_from_location(current_loc_id, char_id)

        await self._world_mgr.add_player_to_location(to_loc_id, char_id)

        # 4. Обновляем account (location.current и location.previous)
        await self._update_player_location(char_id, current_loc_id, to_loc_id)

        log.info(f"ExplorationSession | move_success char_id={char_id} from={current_loc_id} to={to_loc_id}")
        return True

    async def _update_player_location(self, char_id: int, from_loc: str | None, to_loc: str) -> None:
        """
        Обновляет location в account.
        Паттерн аналогичен transition_to_state — сохраняем историю.
        """
        # Формируем новый объект location
        new_location = {
            "current": to_loc,
            "previous": from_loc,
        }
        await self._account_mgr.update_account_fields(char_id, {"location": new_location})

    # =========================================================================
    # HELPERS: Parsing
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
            log.error(f"ExplorationSession | json_parse_error loc_id={loc_id} error={e}")
            return None

    # =========================================================================
    # HELPERS: Travel Time (из exits)
    # =========================================================================

    def get_travel_time(self, from_loc_data: dict[str, Any], to_loc_id: str) -> float:
        """
        Извлекает время перехода из exits текущей локации.
        """
        exits = from_loc_data.get("exits", {})

        # Пробуем разные форматы ключа
        for key_format in [f"nav:{to_loc_id}", to_loc_id]:
            exit_data = exits.get(key_format)
            if exit_data and isinstance(exit_data, dict):
                return float(exit_data.get("time_duration", 0.0))

        return 0.0
