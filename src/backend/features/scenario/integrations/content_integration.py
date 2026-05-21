from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger as log

from src.backend.features.scenario.dto.master import QuestMasterSchema, QuestNodeSchema

if TYPE_CHECKING:
    from src.backend.infrastructure.scenario.managers.content_manager import ScenarioContentManager
    from src.backend.infrastructure.scenario.repositories import ScenarioRepository


class ScenarioContentIntegration:
    """Scenario-owned facade over static content persistence and cache."""

    def __init__(self, repo: ScenarioRepository, cache: ScenarioContentManager) -> None:
        self.repo = repo
        self.cache = cache

    async def get_master(self, quest_key: str) -> dict[str, Any] | None:
        master = await self.cache.get_master(quest_key)
        if master:
            return QuestMasterSchema.model_validate(master).model_dump(mode="json")

        await self.warm_up_cache(quest_key)
        master = await self.cache.get_master(quest_key)
        if master:
            return QuestMasterSchema.model_validate(master).model_dump(mode="json")
        return None

    async def get_node(self, quest_key: str, node_key: str) -> dict[str, Any] | None:
        node = await self.cache.get_node(quest_key, node_key)
        if node:
            return QuestNodeSchema.model_validate(node).model_dump(mode="json")

        await self.warm_up_cache(quest_key)
        node = await self.cache.get_node(quest_key, node_key)
        if node:
            return QuestNodeSchema.model_validate(node).model_dump(mode="json")
        return None

    async def get_nodes_by_pool(self, quest_key: str, pool_tag: str) -> list[dict[str, Any]]:
        await self.warm_up_cache(quest_key)
        nodes = await self.repo.get_nodes_by_pool(quest_key, pool_tag)
        result = [QuestNodeSchema.model_validate(node).model_dump(mode="json") for node in nodes]
        if not result:
            log.bind(quest_key=quest_key, pool_tag=pool_tag).warning("ScenarioPoolEmpty")
        return result

    async def warm_up_cache(self, quest_key: str) -> int:
        master = await self.repo.get_master(quest_key)
        if not master:
            log.bind(quest_key=quest_key, reason="master_not_found").warning("ScenarioCacheWarmupSkipped")
            return 0

        master_data = QuestMasterSchema.model_validate(master).model_dump(mode="json")
        nodes = [
            QuestNodeSchema.model_validate(node).model_dump(mode="json")
            for node in await self.repo.get_all_quest_nodes(quest_key)
        ]
        await self.cache.cache_quest_data(quest_key, master_data, nodes)
        log.bind(quest_key=quest_key, node_count=len(nodes)).info("ScenarioCacheWarmed")
        return len(nodes)

    async def invalidate(self, quest_key: str) -> None:
        await self.cache.invalidate(quest_key)
        log.bind(quest_key=quest_key).info("ScenarioCacheInvalidated")
