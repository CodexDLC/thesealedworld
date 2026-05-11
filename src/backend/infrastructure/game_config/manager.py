from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import redis.asyncio as aioredis

    from src.backend.infrastructure.game_config.base import BaseGameConfig

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConfigEntry:
    key: str
    namespace: str
    current: str
    default: str
    value_type: str  # "int" | "float" | "str" | "bool"


class GameConfigManager:
    """Redis-backed runtime config store.

    On startup: writes all registered config defaults to Redis (SET).
    Services may call get() to read current values; cabinet may call set() to override.
    All changes are in-memory for the lifetime of the Redis server — no database.
    """

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client
        self._registry: dict[str, type[BaseGameConfig]] = {}

    def register(self, config_cls: type[BaseGameConfig]) -> None:
        self._registry[config_cls.namespace] = config_cls
        log.debug(
            "GameConfigManager: registered namespace=%s keys=%s", config_cls.namespace, list(config_cls.defaults())
        )

    async def bootstrap(self) -> None:
        """Write all defaults to Redis on startup (SET, always overwrites)."""
        for config_cls in self._registry.values():
            for key, default in config_cls.defaults().items():
                redis_key = config_cls.redis_key(key)
                await self._redis.set(redis_key, str(default))
        log.info("GameConfigManager: bootstrapped %d namespaces", len(self._registry))

    # ── Read ──────────────────────────────────────────────────────────────────

    def namespaces(self) -> list[str]:
        return list(self._registry.keys())

    async def get(self, namespace: str, key: str) -> str | None:
        config_cls = self._registry.get(namespace)
        if config_cls is None or key not in config_cls.defaults():
            return None
        return await self._redis.get(config_cls.redis_key(key))

    async def list_namespace(self, namespace: str) -> list[ConfigEntry]:
        config_cls = self._registry.get(namespace)
        if config_cls is None:
            return []
        entries: list[ConfigEntry] = []
        for key, default in config_cls.defaults().items():
            current = await self._redis.get(config_cls.redis_key(key))
            entries.append(
                ConfigEntry(
                    key=key,
                    namespace=namespace,
                    current=current if current is not None else str(default),
                    default=str(default),
                    value_type=type(default).__name__,
                )
            )
        return entries

    async def list_all(self) -> dict[str, list[ConfigEntry]]:
        result: dict[str, list[ConfigEntry]] = {}
        for namespace in self._registry:
            result[namespace] = await self.list_namespace(namespace)
        return result

    # ── Write ─────────────────────────────────────────────────────────────────

    async def set(self, namespace: str, key: str, value: str) -> bool:
        config_cls = self._registry.get(namespace)
        if config_cls is None or key not in config_cls.defaults():
            return False
        await self._redis.set(config_cls.redis_key(key), value)
        log.info("GameConfigManager: set %s.%s = %r", namespace, key, value)
        return True

    async def reset(self, namespace: str, key: str) -> bool:
        config_cls = self._registry.get(namespace)
        if config_cls is None:
            return False
        default = config_cls.default_for(key)
        if default is None:
            return False
        await self._redis.set(config_cls.redis_key(key), str(default))
        return True

    async def reset_namespace(self, namespace: str) -> bool:
        config_cls = self._registry.get(namespace)
        if config_cls is None:
            return False
        for key, default in config_cls.defaults().items():
            await self._redis.set(config_cls.redis_key(key), str(default))
        return True
