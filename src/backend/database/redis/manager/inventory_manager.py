from typing import Any

from loguru import logger as log
from redis.asyncio.client import Pipeline

from src.backend.database.redis.redis_key import RedisKeys as Rk
from src.backend.database.redis.redis_service import RedisService


class InventoryManager:
    """
    Менеджер для управления сессией инвентаря в Redis (ac:{char_id}:inventory).
    Использует RedisJSON для хранения структуры.
    """

    SESSION_TTL = 3600  # 1 час

    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service

    # --- Core Session Operations ---

    async def save_session(self, char_id: int, session_data: dict[str, Any]) -> None:
        """
        Сохраняет полную сессию инвентаря.

        Args:
            char_id: ID персонажа.
            session_data: Данные сессии.
        """
        key = Rk.get_inventory_key(char_id)
        # JSON.SET key $ data
        await self.redis_service.json_set(key, "$", session_data)
        await self.redis_service.expire(key, self.SESSION_TTL)
        log.debug(f"InventoryManager | action=save status=success char_id={char_id}")

    async def save_session_batch(self, sessions: dict[int, dict[str, Any]]) -> None:
        """
        Массовое сохранение сессий инвентаря.

        Args:
            sessions: Словарь {char_id: session_data}.
        """
        if not sessions:
            return

        def _save_batch(pipe: Pipeline) -> None:
            for char_id, data in sessions.items():
                key = Rk.get_inventory_key(char_id)
                pipe.json().set(key, "$", data)  # type: ignore
                pipe.expire(key, self.SESSION_TTL)

        await self.redis_service.execute_pipeline(_save_batch)
        log.debug(f"InventoryManager | action=save_batch status=success count={len(sessions)}")

    async def get_session(self, char_id: int) -> dict[str, Any] | None:
        """
        Получает полную сессию. Продлевает TTL.

        Args:
            char_id: ID персонажа.

        Returns:
            dict | None: Данные сессии.
        """
        key = Rk.get_inventory_key(char_id)
        res = await self.redis_service.json_get(key, "$")

        if res:
            await self.redis_service.expire(key, self.SESSION_TTL)
            return res[0]  # RedisJSON возвращает список
        return None

    async def exists(self, char_id: int) -> bool:
        """
        Проверяет наличие активной сессии.

        Args:
            char_id: ID персонажа.

        Returns:
            bool: True, если сессия существует.
        """
        key = Rk.get_inventory_key(char_id)
        return await self.redis_service.key_exists(key)

    async def delete_session(self, char_id: int) -> None:
        """
        Удаляет сессию (например, при выходе или очистке кэша).

        Args:
            char_id: ID персонажа.
        """
        key = Rk.get_inventory_key(char_id)
        await self.redis_service.delete_key(key)
        log.info(f"InventoryManager | action=delete status=success char_id={char_id}")

    # --- View Operations (Optimized) ---

    async def get_equipped(self, char_id: int) -> dict[str, Any] | None:
        """
        Получает только надетые предметы (для отрисовки Куклы).

        Args:
            char_id: ID персонажа.

        Returns:
            dict | None: Надетые предметы.
        """
        key = Rk.get_inventory_key(char_id)
        res = await self.redis_service.json_get(key, "$.equipped")
        if res:
            await self.redis_service.expire(key, self.SESSION_TTL)
            return res[0]
        return None

    async def get_bag_filtered(
        self, char_id: int, item_type: str | None = None, subtype: str | None = None
    ) -> list[dict] | None:
        """
        Получает предметы из сумки с фильтрацией на стороне Redis.

        Args:
            char_id: ID персонажа.
            item_type: Тип предмета (фильтр).
            subtype: Подтип предмета (фильтр, пока не используется в JSONPath).

        Returns:
            list[dict] | None: Список предметов.
        """
        key = Rk.get_inventory_key(char_id)

        path = "$.items.*[?(@.location=='bag')]"

        if item_type and item_type != "all":
            path += f" && @.item_type=='{item_type}'"

        res = await self.redis_service.json_get(key, path)

        if res:
            await self.redis_service.expire(key, self.SESSION_TTL)
            return res
        return None

    async def get_wallet(self, char_id: int) -> dict[str, Any] | None:
        """
        Получает кошелек.

        Args:
            char_id: ID персонажа.

        Returns:
            dict | None: Кошелек.
        """
        key = Rk.get_inventory_key(char_id)
        res = await self.redis_service.json_get(key, "$.wallet")
        if res:
            return res[0]
        return None

    # --- Item Operations (Atomic & Dirty Flag) ---

    async def get_item(self, char_id: int, item_id: int) -> dict | None:
        """
        Ищет предмет по ID в общем списке.

        Args:
            char_id: ID персонажа.
            item_id: ID предмета.

        Returns:
            dict | None: Предмет.
        """
        key = Rk.get_inventory_key(char_id)
        path = f"$.items.{item_id}"
        res = await self.redis_service.json_get(key, path)
        if res:
            return res[0]
        return None

    async def add_item(self, char_id: int, item_id: int, item_data: dict) -> None:
        """
        Добавляет предмет и устанавливает dirty флаг.

        Args:
            char_id: ID персонажа.
            item_id: ID предмета.
            item_data: Данные предмета.
        """
        key = Rk.get_inventory_key(char_id)

        def _add_item_batch(pipe: Pipeline) -> None:
            pipe.json().set(key, f"$.items.{item_id}", item_data)  # type: ignore
            pipe.json().set(key, "$.is_dirty", True)  # type: ignore
            pipe.expire(key, self.SESSION_TTL)

        await self.redis_service.execute_pipeline(_add_item_batch)
        log.debug(f"InventoryManager | action=add_item status=success char_id={char_id} item_id={item_id}")

    async def remove_item(self, char_id: int, item_id: int) -> None:
        """
        Удаляет предмет и устанавливает dirty флаг.

        Args:
            char_id: ID персонажа.
            item_id: ID предмета.
        """
        key = Rk.get_inventory_key(char_id)

        def _remove_item_batch(pipe: Pipeline) -> None:
            pipe.json().delete(key, f"$.items.{item_id}")  # type: ignore
            pipe.json().set(key, "$.is_dirty", True)  # type: ignore
            pipe.expire(key, self.SESSION_TTL)

        await self.redis_service.execute_pipeline(_remove_item_batch)
        log.debug(f"InventoryManager | action=remove_item status=success char_id={char_id} item_id={item_id}")

    async def update_equipped_slot(self, char_id: int, slot: str, item_id: int | None) -> None:
        """
        Обновляет слот экипировки и устанавливает dirty флаг.

        Args:
            char_id: ID персонажа.
            slot: Слот экипировки.
            item_id: ID предмета (или None, если сняли).
        """
        key = Rk.get_inventory_key(char_id)
        path = f"$.equipped.{slot}"

        def _update_slot_batch(pipe: Pipeline) -> None:
            if item_id is None:
                pipe.json().delete(key, path)  # type: ignore
            else:
                pipe.json().set(key, path, item_id)  # type: ignore

            pipe.json().set(key, "$.is_dirty", True)  # type: ignore
            pipe.expire(key, self.SESSION_TTL)

        await self.redis_service.execute_pipeline(_update_slot_batch)
        log.debug(f"InventoryManager | action=update_slot status=success char_id={char_id} slot={slot}")

    async def set_dirty_flag(self, char_id: int, is_dirty: bool = True) -> None:
        """
        Устанавливает флаг изменений.

        Args:
            char_id: ID персонажа.
            is_dirty: Значение флага.
        """
        key = Rk.get_inventory_key(char_id)
        await self.redis_service.json_set(key, "$.is_dirty", is_dirty)
