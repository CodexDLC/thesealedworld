from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from loguru import logger

from src.backend.features.scenario.dto.master import QuestMasterSchema, QuestNodeSchema
from src.backend.infrastructure.scenario.managers.keys import ScenarioStaticKey

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService

    from src.backend.infrastructure.scenario.repositories import ScenarioRepository


class ScenarioContentService:
    STATIC_TTL = 3600

    def __init__(self, repo: ScenarioRepository, redis: RedisService) -> None:
        self.repo = repo
        self.redis = redis
        self.key = ScenarioStaticKey()

    def build_key(self, quest_key: str) -> str:
        return self.key.build(quest_key=quest_key)

    async def get_master(self, quest_key: str) -> dict[str, Any] | None:
        key = self.build_key(quest_key)
        cached = await self.redis.hash.get_field(key, "master")
        if cached:
            return QuestMasterSchema.model_validate(json.loads(cached)).model_dump(mode="json")

        master = await self.repo.get_master(quest_key)
        if master is None:
            logger.warning("Scenario master not found: quest_key={}", quest_key)
            return None
        data = QuestMasterSchema.model_validate(master).model_dump(mode="json")
        await self.redis.hash.set_field(key, "master", json.dumps(data, ensure_ascii=False))
        await self.redis.string.expire(key, self.STATIC_TTL)
        logger.info("Scenario master cached: quest_key={}", quest_key)
        return data

    async def get_node(self, quest_key: str, node_key: str) -> dict[str, Any] | None:
        key = self.build_key(quest_key)
        cached = await self.redis.hash.get_field(key, f"node:{node_key}")
        if cached:
            return QuestNodeSchema.model_validate(json.loads(cached)).model_dump(mode="json")

        node = await self.repo.get_node(quest_key, node_key)
        if node is None:
            logger.warning("Scenario node not found: quest_key={} node_key={}", quest_key, node_key)
            return None
        data = QuestNodeSchema.model_validate(node).model_dump(mode="json")
        await self.redis.hash.set_field(key, f"node:{node_key}", json.dumps(data, ensure_ascii=False))
        await self.redis.string.expire(key, self.STATIC_TTL)
        logger.info("Scenario node cached: quest_key={} node_key={}", quest_key, node_key)
        return data

    async def get_nodes_by_pool(self, quest_key: str, pool_tag: str) -> list[dict[str, Any]]:
        nodes = [
            QuestNodeSchema.model_validate(node).model_dump(mode="json")
            for node in await self.repo.get_nodes_by_pool(quest_key, pool_tag)
        ]
        if not nodes:
            logger.warning("Scenario pool returned no nodes: quest_key={} pool_tag={}", quest_key, pool_tag)
        return nodes

    async def warm_up_cache(self, quest_key: str) -> int:
        """Loads all nodes for a quest from DB into Redis cache."""
        master = await self.repo.get_master(quest_key)
        if not master:
            logger.warning("Scenario cache warmup skipped: master_not_found quest_key={}", quest_key)
            return 0

        nodes = await self.repo.get_all_quest_nodes(quest_key)
        key = self.build_key(quest_key)

        mapping = {
            "master": json.dumps(QuestMasterSchema.model_validate(master).model_dump(mode="json"), ensure_ascii=False)
        }
        for node in nodes:
            data = QuestNodeSchema.model_validate(node).model_dump(mode="json")
            mapping[f"node:{node['node_key']}"] = json.dumps(data, ensure_ascii=False)

        if mapping:
            await self.redis.hash.set_fields(key, mapping)
            await self.redis.string.expire(key, self.STATIC_TTL)

        logger.info("Scenario cache warmed: quest_key={} nodes={}", quest_key, len(nodes))
        return len(nodes)

    async def invalidate(self, quest_key: str) -> None:
        if self.redis:
            await self.redis.string.delete(self.build_key(quest_key))
            logger.info("Scenario cache invalidated: quest_key={}", quest_key)
