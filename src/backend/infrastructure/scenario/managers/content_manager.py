from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from src.backend.infrastructure.scenario.managers.keys import ScenarioStaticKey

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService


class ScenarioContentManager:
    STATIC_TTL = 3600

    def __init__(self, redis: RedisService) -> None:
        self.redis = redis
        self.key = ScenarioStaticKey()

    def build_key(self, quest_key: str) -> str:
        return self.key.build(quest_key=quest_key)

    async def get_master(self, quest_key: str) -> dict[str, Any] | None:
        key = self.build_key(quest_key)
        cached = await self.redis.hash.get_field(key, "master")
        if cached:
            return json.loads(cached)
        return None

    async def set_master(self, quest_key: str, data: dict[str, Any]) -> None:
        key = self.build_key(quest_key)
        await self.redis.hash.set_field(key, "master", json.dumps(data, ensure_ascii=False))
        await self.redis.string.expire(key, self.STATIC_TTL)

    async def get_node(self, quest_key: str, node_key: str) -> dict[str, Any] | None:
        key = self.build_key(quest_key)
        cached = await self.redis.hash.get_field(key, f"node:{node_key}")
        if cached:
            return json.loads(cached)
        return None

    async def set_node(self, quest_key: str, node_key: str, data: dict[str, Any]) -> None:
        key = self.build_key(quest_key)
        await self.redis.hash.set_field(key, f"node:{node_key}", json.dumps(data, ensure_ascii=False))
        await self.redis.string.expire(key, self.STATIC_TTL)

    async def get_all_nodes(self, quest_key: str) -> list[dict[str, Any]]:
        key = self.build_key(quest_key)
        all_data = await self.redis.hash.get_all(key)
        nodes = []
        if all_data:
            for k, v in all_data.items():
                if k.startswith("node:"):
                    try:
                        nodes.append(json.loads(v))
                    except (json.JSONDecodeError, TypeError):
                        continue
        return nodes

    async def cache_quest_data(self, quest_key: str, master: dict[str, Any], nodes: list[dict[str, Any]]) -> None:
        key = self.build_key(quest_key)
        updates = {"master": json.dumps(master, ensure_ascii=False)}
        for node in nodes:
            node_key = node["node_key"]
            updates[f"node:{node_key}"] = json.dumps(node, ensure_ascii=False)
        
        # We can use multiple set_field or just loop (hash.set_field doesn't easily support MSET in the current RedisService signature, but we'll loop for safety unless hmset is available)
        for k, v in updates.items():
            await self.redis.hash.set_field(key, k, v)
        await self.redis.string.expire(key, self.STATIC_TTL)

    async def exists(self, quest_key: str) -> bool:
        key = self.build_key(quest_key)
        return bool(await self.redis.string.exists(key))
