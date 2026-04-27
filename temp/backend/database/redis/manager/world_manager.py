from loguru import logger as log

from src.backend.database.redis.redis_key import RedisKeys as Rk
from src.backend.database.redis.redis_service import RedisService


class WorldManager:
    """
    Менеджер для управления данными о мировых локациях и игроках в них в Redis.

    Предоставляет CRUD-операции для метаданных локаций и списков игроков,
    находящихся в каждой локации.
    """

    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service

    async def write_location_meta(self, loc_id: str, data: dict) -> None:
        """
        Записывает или обновляет метаданные для указанной мировой локации.

        Args:
            loc_id: Уникальный идентификатор локации.
            data: Словарь с метаданными локации (например, название, описание, выходы).
        """
        key = Rk.get_world_location_meta_key(loc_id)
        await self.redis_service.set_hash_fields(key, data)
        log.debug(f"WorldManager | action=write_meta status=success loc_id={loc_id}")

    async def get_location_meta(self, loc_id: str) -> dict | None:
        """
        Получает все метаданные для указанной мировой локации.

        Args:
            loc_id: Уникальный идентификатор локации.

        Returns:
            Словарь с метаданными локации, или None, если метаданные не найдены.
        """
        key = Rk.get_world_location_meta_key(loc_id)
        return await self.redis_service.get_all_hash(key)

    async def location_meta_exists(self, loc_id: str) -> bool:
        """
        Проверяет существование метаданных для указанной мировой локации.

        Args:
            loc_id: Уникальный идентификатор локации.

        Returns:
            True, если метаданные локации существуют, иначе False.
        """
        key = Rk.get_world_location_meta_key(loc_id)
        return await self.redis_service.key_exists(key)

    async def add_player_to_location(self, loc_id: str, char_id: int) -> None:
        """
        Добавляет игрока в множество игроков, находящихся в указанной локации.

        Args:
            loc_id: Уникальный идентификатор локации.
            char_id: Идентификатор персонажа, который входит в локацию.
        """
        key = Rk.get_world_location_players_key(loc_id)
        await self.redis_service.add_to_set(key, char_id)
        log.debug(f"WorldManager | action=add_player status=success loc_id={loc_id} char_id={char_id}")

    async def remove_player_from_location(self, loc_id: str, char_id: int) -> None:
        """
        Удаляет игрока из множества игроков, находящихся в указанной локации.

        Args:
            loc_id: Уникальный идентификатор локации.
            char_id: Идентификатор персонажа, который покидает локацию.
        """
        key = Rk.get_world_location_players_key(loc_id)
        await self.redis_service.remove_from_set(key, char_id)
        log.debug(f"WorldManager | action=remove_player status=success loc_id={loc_id} char_id={char_id}")

    async def get_players_in_location(self, loc_id: str) -> set[str]:
        """
        Получает список всех игроков, находящихся в указанной локации.

        Args:
            loc_id: Уникальный идентификатор локации.

        Returns:
            Множество строковых идентификаторов персонажей в локации.
        """
        key = Rk.get_world_location_players_key(loc_id)
        return await self.redis_service.get_set_members(key)

    # --- Battles Management (Hash: battle_id -> description) ---

    async def add_battle_to_location(self, loc_id: str, battle_id: str, description: str) -> None:
        """
        Добавляет бой в список активных боев локации.
        Использует Hash, где ключ=battle_id, значение=описание.

        Args:
            loc_id: ID локации.
            battle_id: ID боя.
            description: Описание боя.
        """
        key = Rk.get_world_location_battles_key(loc_id)
        await self.redis_service.set_hash_field(key, battle_id, description)
        log.debug(f"WorldManager | action=add_battle status=success loc_id={loc_id} battle_id={battle_id}")

    async def remove_battle_from_location(self, loc_id: str, battle_id: str) -> None:
        """
        Удаляет бой из списка активных боев локации.

        Args:
            loc_id: ID локации.
            battle_id: ID боя.
        """
        key = Rk.get_world_location_battles_key(loc_id)
        await self.redis_service.delete_hash_field(key, battle_id)
        log.debug(f"WorldManager | action=remove_battle status=success loc_id={loc_id} battle_id={battle_id}")

    async def get_battles_in_location(self, loc_id: str) -> dict[str, str]:
        """
        Получает словарь активных боев: {battle_id: description}.

        Args:
            loc_id: ID локации.

        Returns:
            dict: Словарь боев.
        """
        key = Rk.get_world_location_battles_key(loc_id)
        return await self.redis_service.get_all_hash(key) or {}
