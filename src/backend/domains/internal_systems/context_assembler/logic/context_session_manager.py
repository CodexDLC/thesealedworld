import uuid
from typing import Any

from src.backend.database.redis.manager.context_manager import ContextRedisManager
from src.backend.database.redis.manager.inventory_manager import InventoryManager
from src.backend.database.redis.redis_key import RedisKeys as Rk


class ContextSessionManager:
    """
    Фасад для управления сохранением контекстов в Redis.
    Изолирует ассемблеры от деталей реализации Redis (ключи, типы данных).
    Агрегирует специализированные менеджеры (InventoryManager, etc.) и общий ContextRedisManager.
    """

    def __init__(self, context_redis_manager: ContextRedisManager, inventory_manager: InventoryManager):
        self.context_manager = context_redis_manager
        self.inventory_manager = inventory_manager

    async def save_player_batch(self, scope: str, contexts: dict[int, dict[str, Any]]) -> dict[int, str]:
        """
        Сохраняет пакет контекстов игроков в зависимости от scope.

        Args:
            scope: Область видимости (inventory, combats, etc.)
            contexts: Словарь {char_id: context_data}

        Returns:
            Словарь {char_id: redis_key}
        """
        if not contexts:
            return {}

        result_map: dict[int, str] = {}

        # Стратегия выбора ключей и метода сохранения
        if scope == "inventory":
            # Используем InventoryManager для сохранения (RedisJSON)
            await self.inventory_manager.save_session_batch(contexts)

            # Генерируем ключи для ответа (чтобы сервис знал, где искать)
            for char_id in contexts:
                result_map[char_id] = Rk.get_inventory_key(char_id)

        elif scope == "combats":
            # Для боя используем временные ключи и String JSON (через ContextManager)
            # Данные будут распакованы Combat Domain
            batch_data = {}
            for char_id, data in contexts.items():
                key = f"temp:setup:{uuid.uuid4()}"
                result_map[char_id] = key
                batch_data[char_id] = (key, data)

            await self.context_manager.save_context_batch(batch_data)

        elif scope == "status":
            # TODO: Реализовать StatusManager и сохранение в ac:{char_id}:status (будет позже)
            # Пока используем temp
            batch_data = {}
            for char_id, data in contexts.items():
                key = f"temp:setup:{uuid.uuid4()}"
                result_map[char_id] = key
                batch_data[char_id] = (key, data)

            await self.context_manager.save_context_batch(batch_data)

        else:
            # Default: Temp keys
            batch_data = {}
            for char_id, data in contexts.items():
                key = f"temp:setup:{uuid.uuid4()}"
                result_map[char_id] = key
                batch_data[char_id] = (key, data)

            await self.context_manager.save_context_batch(batch_data)

        return result_map
