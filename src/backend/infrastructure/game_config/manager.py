from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, overload

from loguru import logger as log

if TYPE_CHECKING:
    import redis.asyncio as aioredis

    from src.backend.infrastructure.game_config.base import BaseGameConfig, ConfigValue


@dataclass(frozen=True)
class ConfigEntry:
    key: str
    namespace: str
    current: str
    default: str
    value_type: str  # "int" | "float" | "str" | "bool"


_BOOL_TRUE = {"true", "1", "yes"}
_BOOL_FALSE = {"false", "0", "no"}


class GameConfigManager:
    """Redis-backed runtime config store.

    On startup: writes registered defaults to Redis only for missing keys (SET NX),
    so admin overrides set via cabinet/API survive backend restarts.
    Services read values via get/get_str/get_int/get_float/get_bool; cabinet writes via set/reset.
    """

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client
        self._registry: dict[str, type[BaseGameConfig]] = {}

    def register(self, config_cls: type[BaseGameConfig]) -> None:
        self._registry[config_cls.namespace] = config_cls
        log.bind(namespace=config_cls.namespace, keys=list(config_cls.defaults())).debug(
            "GameConfigNamespaceRegistered"
        )

    async def bootstrap(self) -> None:
        """Write defaults to Redis only for keys that don't exist yet (preserves overrides)."""
        written = 0
        preserved = 0
        for config_cls in self._registry.values():
            for key, default in config_cls.defaults().items():
                redis_key = config_cls.redis_key(key)
                if await self._redis.set(redis_key, str(default), nx=True):
                    written += 1
                else:
                    preserved += 1
        log.bind(
            namespace_count=len(self._registry),
            keys_written=written,
            keys_preserved=preserved,
        ).info("GameConfigBootstrapped")

    # ── Read ──────────────────────────────────────────────────────────────────

    def namespaces(self) -> list[str]:
        return list(self._registry.keys())

    async def get(self, namespace: str, key: str) -> str | None:
        config_cls = self._registry.get(namespace)
        if config_cls is None or key not in config_cls.defaults():
            return None
        return await self._redis.get(config_cls.redis_key(key))

    @overload
    async def get_str(self, namespace: str, key: str, default: str) -> str: ...
    @overload
    async def get_str(self, namespace: str, key: str, default: None = None) -> str | None: ...
    async def get_str(self, namespace: str, key: str, default: str | None = None) -> str | None:
        registered_default = self._registered_default(namespace, key)
        if registered_default is None:
            return default
        raw = await self._redis.get(self._registry[namespace].redis_key(key))
        if raw is None:
            return str(registered_default)
        return str(raw)

    @overload
    async def get_int(self, namespace: str, key: str, default: int) -> int: ...
    @overload
    async def get_int(self, namespace: str, key: str, default: None = None) -> int | None: ...
    async def get_int(self, namespace: str, key: str, default: int | None = None) -> int | None:
        return await self._coerce(namespace, key, default, int, _to_int)

    @overload
    async def get_float(self, namespace: str, key: str, default: float) -> float: ...
    @overload
    async def get_float(self, namespace: str, key: str, default: None = None) -> float | None: ...
    async def get_float(self, namespace: str, key: str, default: float | None = None) -> float | None:
        return await self._coerce(namespace, key, default, float, _to_float)

    @overload
    async def get_bool(self, namespace: str, key: str, default: bool) -> bool: ...
    @overload
    async def get_bool(self, namespace: str, key: str, default: None = None) -> bool | None: ...
    async def get_bool(self, namespace: str, key: str, default: bool | None = None) -> bool | None:
        return await self._coerce(namespace, key, default, bool, _to_bool)

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
        log.bind(namespace=namespace, key=key).info("GameConfigSet")
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

    # ── Internal ──────────────────────────────────────────────────────────────

    def _registered_default(self, namespace: str, key: str) -> ConfigValue | None:
        config_cls = self._registry.get(namespace)
        if config_cls is None:
            return None
        defaults = config_cls.defaults()
        if key not in defaults:
            return None
        return defaults[key]

    async def _coerce(
        self,
        namespace: str,
        key: str,
        caller_default,
        target_type,
        parser,
    ):
        registered_default = self._registered_default(namespace, key)
        if registered_default is None:
            return caller_default
        raw = await self._redis.get(self._registry[namespace].redis_key(key))
        if raw is None:
            return self._cast_default(registered_default, target_type, caller_default)
        parsed = parser(raw)
        if parsed is None:
            log.bind(namespace=namespace, key=key, raw=str(raw)).warning("GameConfigCoercionFailed")
            return self._cast_default(registered_default, target_type, caller_default)
        return parsed

    @staticmethod
    def _cast_default(registered_default, target_type, caller_default):
        if isinstance(registered_default, target_type):
            return registered_default
        try:
            return target_type(registered_default)
        except (TypeError, ValueError):
            return caller_default


def _to_int(raw: object) -> int | None:
    try:
        return int(str(raw))
    except (TypeError, ValueError):
        try:
            return int(float(str(raw)))
        except (TypeError, ValueError):
            return None


def _to_float(raw: object) -> float | None:
    try:
        return float(str(raw))
    except (TypeError, ValueError):
        return None


def _to_bool(raw: object) -> bool | None:
    token = str(raw).strip().lower()
    if token in _BOOL_TRUE:
        return True
    if token in _BOOL_FALSE:
        return False
    return None
