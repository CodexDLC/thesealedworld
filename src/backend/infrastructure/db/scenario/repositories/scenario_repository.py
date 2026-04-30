from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from src.backend.infrastructure.db.scenario.models import CharacterQuestState, ScenarioMaster, ScenarioNode

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


class ScenarioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_master(self, quest_key: str) -> dict[str, Any] | None:
        result = await self.session.execute(select(ScenarioMaster).where(ScenarioMaster.quest_key == quest_key))
        obj = result.scalar_one_or_none()
        if obj is None:
            return None
        return {
            **obj.master_data,
            "quest_key": obj.quest_key,
            "start_node_id": obj.start_node_id,
            "status_bar_fields": obj.status_bar_fields,
            "config": obj.config,
        }

    async def upsert_master(self, master_data: dict[str, Any]) -> None:
        quest_key = str(master_data["quest_key"])
        values = {
            "quest_key": quest_key,
            "display_name": master_data["display_name"],
            "start_node_id": master_data["start_node_id"],
            "master_data": master_data,
            "status_bar_fields": master_data.get("status_bar_fields", []),
            "config": master_data.get("config"),
        }
        stmt = insert(ScenarioMaster).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[ScenarioMaster.quest_key],
            set_={key: value for key, value in values.items() if key != "quest_key"},
        )
        await self.session.execute(stmt)

    async def get_node(self, quest_key: str, node_key: str) -> dict[str, Any] | None:
        stmt = select(ScenarioNode).where(ScenarioNode.quest_key == quest_key, ScenarioNode.node_key == node_key)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return self._node_to_dict(obj) if obj is not None else None

    async def get_nodes_by_pool(self, quest_key: str, pool_tag: str) -> list[dict[str, Any]]:
        stmt = select(ScenarioNode).where(ScenarioNode.quest_key == quest_key, ScenarioNode.tags.contains([pool_tag]))
        result = await self.session.execute(stmt)
        return [self._node_to_dict(obj) for obj in result.scalars().all()]

    async def get_all_quest_nodes(self, quest_key: str) -> list[dict[str, Any]]:
        result = await self.session.execute(select(ScenarioNode).where(ScenarioNode.quest_key == quest_key))
        return [self._node_to_dict(obj) for obj in result.scalars().all()]

    async def bulk_insert_nodes(self, nodes: list[dict[str, Any]]) -> None:
        if not nodes:
            return
        values = [
            {
                "quest_key": node["quest_key"],
                "node_key": node["node_key"],
                "display_name": node.get("display_name"),
                "text": node.get("text", ""),
                "icon": node.get("icon"),
                "alerts": node.get("alerts", []),
                "node_data": node,
                "tags": node.get("tags", []),
            }
            for node in nodes
        ]
        stmt = insert(ScenarioNode).values(values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_scenario_nodes_quest_node_key",
            set_={
                "display_name": stmt.excluded.display_name,
                "text": stmt.excluded.text,
                "icon": stmt.excluded.icon,
                "alerts": stmt.excluded.alerts,
                "node_data": stmt.excluded.node_data,
                "tags": stmt.excluded.tags,
            },
        )
        await self.session.execute(stmt)

    async def delete_quest_nodes(self, quest_key: str) -> None:
        await self.session.execute(delete(ScenarioNode).where(ScenarioNode.quest_key == quest_key))

    async def get_active_state(self, char_id: int) -> dict[str, Any] | None:
        result = await self.session.execute(
            select(CharacterQuestState).where(CharacterQuestState.character_id == char_id)
        )
        obj = result.scalar_one_or_none()
        if obj is None:
            return None
        return {
            "character_id": obj.character_id,
            "quest_key": obj.quest_key,
            "node_key": obj.node_key,
            "context": obj.context,
            "session_id": obj.session_id,
        }

    async def upsert_state(
        self,
        char_id: int,
        quest_key: str,
        node_key: str,
        context: dict[str, Any],
        session_id: uuid.UUID,
    ) -> None:
        values = {
            "character_id": char_id,
            "quest_key": quest_key,
            "node_key": node_key,
            "context": context,
            "session_id": session_id,
        }
        stmt = insert(CharacterQuestState).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[CharacterQuestState.character_id],
            set_={key: value for key, value in values.items() if key != "character_id"},
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def delete_state(self, char_id: int) -> None:
        await self.session.execute(delete(CharacterQuestState).where(CharacterQuestState.character_id == char_id))
        await self.session.commit()

    @staticmethod
    def _node_to_dict(obj: ScenarioNode) -> dict[str, Any]:
        return {
            **obj.node_data,
            "quest_key": obj.quest_key,
            "node_key": obj.node_key,
            "tags": obj.tags,
        }
