import json
from typing import Any

from loguru import logger as log
from redis.asyncio.client import Pipeline
from redis.exceptions import RedisError

from src.backend.database.redis.redis_service import RedisService


class ContextRedisManager:
    """
    Менеджер для работы с временными контекстами (снапшотами) в Redis.
    Используется ContextAssembler для сохранения результатов сборки.
    """

    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service

    async def save_context_batch(self, data_map: dict[Any, tuple[str, dict[str, Any]]], ttl: int = 90) -> None:
        """
        Массовое сохранение контекстов в Redis (как String JSON).
        Используется для временных контекстов (temp:setup:...).

        Args:
            data_map: Словарь {entity_id: (redis_key, context_data_dict)}.
            ttl: Время жизни ключа в секундах.
        """
        if not data_map:
            return

        def _fill_pipeline(pipe: Pipeline) -> None:
            for _, (key, data) in data_map.items():
                try:
                    json_data = json.dumps(data)
                    pipe.set(key, json_data, ex=ttl)
                except (TypeError, ValueError) as e:
                    log.error(f"ContextRedisManager | serialization failed key={key} error={e}")

        await self.redis_service.execute_pipeline(_fill_pipeline)
        log.debug(f"ContextRedisManager | action=save_batch status=success count={len(data_map)}")

    async def save_json_batch(self, data_map: dict[Any, tuple[str, dict[str, Any]]], ttl: int = 3600) -> None:
        """
        Массовое сохранение контекстов в Redis как RedisJSON (ReJSON).
        Используется для постоянных сессий (например, Inventory).

        Args:
            data_map: Словарь {entity_id: (redis_key, context_data_dict)}.
            ttl: Время жизни ключа в секундах.
        """
        if not data_map:
            return

        def _fill_pipeline(pipe: Pipeline) -> None:
            for _, (key, data) in data_map.items():
                try:
                    # Используем JSON.SET key $ data
                    pipe.json().set(key, "$", data)  # type: ignore
                    pipe.expire(key, ttl)
                except RedisError as e:
                    log.error(f"ContextRedisManager | json save failed key={key} error={e}")
                except Exception as e:  # noqa: BLE001
                    log.error(f"ContextRedisManager | unexpected error key={key} error={e}")

        await self.redis_service.execute_pipeline(_fill_pipeline)
        log.debug(f"ContextRedisManager | action=save_json_batch status=success count={len(data_map)}")

    async def get_context(self, key: str) -> dict[str, Any] | None:
        """
        Получение контекста по ключу.

        Args:
            key: Ключ Redis.

        Returns:
            dict | None: Контекст или None.
        """
        data = await self.redis_service.get_value(key)
        if not data:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            log.error(f"ContextRedisManager | decode failed key={key}")
            return None

    async def get_context_batch(self, keys: list[str]) -> dict[str, dict[str, Any]]:
        """
        Массовое получение контекстов по списку ключей.

        Args:
            keys: Список ключей.

        Returns:
            dict: Словарь {key: context}.
        """
        if not keys:
            return {}

        def _fill_get_pipe(pipe: Pipeline) -> None:
            for key in keys:
                pipe.get(key)

        values = await self.redis_service.execute_pipeline(_fill_get_pipe)
        result = {}

        for key, val in zip(keys, values, strict=False):
            if val:
                try:
                    result[key] = json.loads(val)
                except json.JSONDecodeError:
                    log.error(f"ContextRedisManager | decode failed key={key}")

        return result
