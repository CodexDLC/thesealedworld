from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from src.backend.features.scenario.dto.master import QuestFileSchema, QuestMasterSchema, QuestNodeSchema
from src.backend.infrastructure.scenario.repositories import ScenarioRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.backend.features.scenario.services.content_service import ScenarioContentService


class ScenarioLoader:
    def __init__(self, session: AsyncSession, content: ScenarioContentService | None = None) -> None:
        self.repo = ScenarioRepository(session)
        self.content = content

    async def load_from_file(self, path: str | Path) -> str:
        path = Path(path)
        logger.info("Scenario fixture load started: path={}", path)

        if path.is_dir():
            # Directory loading logic
            master_file = path / "master.json"
            if not master_file.exists():
                logger.warning("Scenario fixture master is missing: path={}", master_file)
                raise FileNotFoundError(f"master.json not found in {path}")

            with master_file.open(encoding="utf-8") as h:
                master_data = QuestMasterSchema.model_validate(json.load(h)).model_dump(mode="json")

            quest_key = master_data["quest_key"]
            all_nodes = []
            node_files = self._discover_node_files(path)

            for node_file in node_files:
                with node_file.open(encoding="utf-8") as h:
                    file_nodes = json.load(h)
                    if not isinstance(file_nodes, list):
                        raise ValueError(f"Scenario node file must contain a list: {node_file}")
                    for n in file_nodes:
                        n["quest_key"] = master_data["quest_key"]

                    validated = [QuestNodeSchema.model_validate(n).model_dump(mode="json") for n in file_nodes]
                    all_nodes.extend(validated)
        else:
            # Legacy single file loading
            with path.open(encoding="utf-8") as handle:
                parsed = QuestFileSchema.model_validate(json.load(handle))
            master_data = parsed.master.model_dump(mode="json")
            quest_key = master_data["quest_key"]
            all_nodes = [node.model_dump(mode="json") for node in parsed.nodes]

        all_nodes = [{**node, "quest_key": quest_key} for node in all_nodes]

        # Deduplicate all nodes by (quest_key, node_key) to prevent DB IntegrityErrors
        deduplicated = {}
        for node in all_nodes:
            key = (node["quest_key"], node["node_key"])
            if key in deduplicated:
                logger.warning(f"Duplicate node_key found in scenario files: {key}. Keeping last one.")
            deduplicated[key] = node

        all_nodes = list(deduplicated.values())

        await self.repo.upsert_master(master_data)
        await self.repo.delete_quest_nodes(quest_key)
        await self.repo.bulk_insert_nodes(all_nodes)
        await self.repo.session.commit()

        if self.content is not None:
            cached_nodes = await self.content.warm_up_cache(quest_key)
            logger.info("Scenario fixture cache warmed: quest_key={} nodes={}", quest_key, cached_nodes)
        logger.info("Scenario fixture load finished: quest_key={} nodes={}", quest_key, len(all_nodes))
        return quest_key

    @staticmethod
    def _discover_node_files(path: Path) -> list[Path]:
        nodes_dir = path / "nodes"
        if nodes_dir.exists():
            return sorted(nodes_dir.glob("*.json"))
        return sorted(path.glob("nodes_*.json"))
