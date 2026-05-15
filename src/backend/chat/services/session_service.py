import json
from typing import Any, cast

import redis.asyncio as aioredis


class PlayerChatSession:
    """Hot player chat state stored in Redis Hash — location, party, open DM sessions."""

    _KEY = "chat:session:{character_id}"

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    def _key(self, character_id: str) -> str:
        return self._KEY.format(character_id=character_id)

    async def get_state(self, character_id: str) -> dict[str, Any]:
        data = await cast("Any", self._redis.hgetall(self._key(character_id)))
        if "dm_sessions" in data:
            data["dm_sessions"] = json.loads(data["dm_sessions"])
        return data

    async def set_sender_name(self, character_id: str, name: str) -> None:
        await cast("Any", self._redis.hset(self._key(character_id), "sender_name", name))

    async def set_location(self, character_id: str, location_id: str) -> None:
        await cast("Any", self._redis.hset(self._key(character_id), "location_id", location_id))

    async def set_party(self, character_id: str, party_id: str | None) -> None:
        key = self._key(character_id)
        if party_id:
            await cast("Any", self._redis.hset(key, "party_id", party_id))
        else:
            await cast("Any", self._redis.hdel(key, "party_id"))

    async def open_dm(self, character_id: str, session_id: str) -> None:
        key = self._key(character_id)
        raw = await cast("Any", self._redis.hget(key, "dm_sessions"))
        sessions: list[str] = json.loads(raw) if raw else []
        if session_id not in sessions:
            sessions.append(session_id)
        await cast("Any", self._redis.hset(key, "dm_sessions", json.dumps(sessions)))

    async def close_dm(self, character_id: str, session_id: str) -> None:
        key = self._key(character_id)
        raw = await cast("Any", self._redis.hget(key, "dm_sessions"))
        sessions: list[str] = json.loads(raw) if raw else []
        sessions = [s for s in sessions if s != session_id]
        await cast("Any", self._redis.hset(key, "dm_sessions", json.dumps(sessions)))

    async def clear(self, character_id: str) -> None:
        await self._redis.delete(self._key(character_id))
