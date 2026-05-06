from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.backend.features.scenario.dto.master import QuestMasterSchema, QuestNodeSchema

if TYPE_CHECKING:
    from src.backend.infrastructure.scenario.managers.content_manager import ScenarioContentManager
    from src.backend.infrastructure.scenario.repositories import ScenarioRepository

log = logging.getLogger(__name__)


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
            log.warning("Scenario pool returned no nodes: quest_key=%s pool_tag=%s", quest_key, pool_tag)
        return result

    async def warm_up_cache(self, quest_key: str) -> int:
        master = await self.repo.get_master(quest_key)
        if not master:
            log.warning("Scenario cache warmup skipped: master_not_found quest_key=%s", quest_key)
            return 0

        master_data = QuestMasterSchema.model_validate(master).model_dump(mode="json")
        nodes = [
            QuestNodeSchema.model_validate(node).model_dump(mode="json")
            for node in await self.repo.get_all_quest_nodes(quest_key)
        ]
        await self.cache.cache_quest_data(quest_key, master_data, nodes)
        log.info("Scenario cache warmed: quest_key=%s nodes=%s", quest_key, len(nodes))
        return len(nodes)

    async def invalidate(self, quest_key: str) -> None:
        await self.cache.invalidate(quest_key)
        log.info("Scenario cache invalidated: quest_key=%s", quest_key)
