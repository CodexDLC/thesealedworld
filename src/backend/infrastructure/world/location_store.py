from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.infrastructure.redis.keys import WorldLocationBattlesKey, WorldLocationKey, WorldLocationPlayersKey

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService


class WorldLocationStore:
    def __init__(self, redis: RedisService) -> None:
        self.redis = redis
        self.location_key = WorldLocationKey()
        self.players_key = WorldLocationPlayersKey()
        self.battles_key = WorldLocationBattlesKey()

    def build_location_key(self, loc_id: str) -> str:
        return self.location_key.build(loc_id=loc_id)

    def build_players_key(self, loc_id: str) -> str:
        return self.players_key.build(loc_id=loc_id)

    def build_battles_key(self, loc_id: str) -> str:
        return self.battles_key.build(loc_id=loc_id)

    def _redis_client(self) -> Any:
        if hasattr(self.redis, "redis_client"):
            return self.redis.redis_client
        return self.redis.pipeline.client

    async def write_location(self, loc_id: str, data: dict[str, Any]) -> None:
        await self.redis.json_module.set(self.build_location_key(loc_id), "$", data)

    async def write_locations(self, locations: dict[str, dict[str, Any]]) -> int:
        if not locations:
            return 0

        async with self._redis_client().pipeline(transaction=False) as pipe:
            for loc_id, data in locations.items():
                pipe.json().set(self.build_location_key(loc_id), "$", data)
            results = await pipe.execute(raise_on_error=False)

        return sum(1 for result in results if not isinstance(result, Exception) and result)

    async def get_location(self, loc_id: str) -> dict[str, Any] | None:
        result = await self.redis.json_module.get(self.build_location_key(loc_id), "$")
        doc = self._first(result)
        return doc if isinstance(doc, dict) else None

    async def location_exists(self, loc_id: str) -> bool:
        return bool(await self.redis.string.exists(self.build_location_key(loc_id)))

    async def add_player(self, loc_id: str, char_id: int) -> None:
        await self._redis_client().sadd(self.build_players_key(loc_id), str(char_id))

    async def remove_player(self, loc_id: str, char_id: int) -> None:
        await self._redis_client().srem(self.build_players_key(loc_id), str(char_id))

    async def get_players(self, loc_id: str) -> set[str]:
        return set(await self._redis_client().smembers(self.build_players_key(loc_id)))

    async def add_battle(self, loc_id: str, battle_id: str, description: str) -> None:
        await self._redis_client().hset(self.build_battles_key(loc_id), battle_id, description)

    async def remove_battle(self, loc_id: str, battle_id: str) -> None:
        await self._redis_client().hdel(self.build_battles_key(loc_id), battle_id)

    async def get_battles(self, loc_id: str) -> dict[str, str]:
        return dict(await self._redis_client().hgetall(self.build_battles_key(loc_id)))

    @staticmethod
    def _first(result: Any) -> Any:
        if isinstance(result, list):
            return result[0] if result else None
        return result
