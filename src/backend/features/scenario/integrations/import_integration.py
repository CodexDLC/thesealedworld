from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger

from src.backend.features.scenario.integrations.content_integration import ScenarioContentIntegration
from src.backend.infrastructure.scenario.repositories import ScenarioRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.backend.infrastructure.scenario.managers.content_manager import ScenarioContentManager


class ScenarioImportIntegration:
    """Scenario-owned import gateway for writing quest fixtures to persistence."""

    def __init__(self, repo: ScenarioRepository, content: ScenarioContentIntegration | None = None) -> None:
        self.repo = repo
        self.content = content

    @classmethod
    def from_session(
        cls,
        session: AsyncSession,
        *,
        cache: ScenarioContentManager | None = None,
    ) -> ScenarioImportIntegration:
        repo = ScenarioRepository(session)
        content = ScenarioContentIntegration(repo, cache) if cache is not None else None
        return cls(repo, content)

    async def replace_quest(self, master_data: dict[str, Any], nodes: list[dict[str, Any]]) -> int | None:
        quest_key = str(master_data["quest_key"])

        await self.repo.replace_quest(master_data, nodes)

        if self.content is None:
            return None

        cached_nodes = await self.content.warm_up_cache(quest_key)
        logger.bind(quest_key=quest_key, node_count=cached_nodes).info("ScenarioFixtureCacheWarmed")
        return cached_nodes
