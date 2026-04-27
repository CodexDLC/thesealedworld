from typing import Any
from uuid import UUID

from loguru import logger as log
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.db_contract.i_scenario_repo import IScenarioRepository
from src.backend.database.postgres.models.scenario import CharacterScenarioState, ScenarioMaster, ScenarioNode


class ScenarioRepositoryORM(IScenarioRepository):
    """
    Реализация репозитория сценариев на SQLAlchemy 2.0.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        log.debug(f"ScenarioRepositoryORM | status=initialized session={session}")

    # --- 1. Работа с Scenario_Master (Table A) ---

    async def get_master(self, quest_key: str) -> dict[str, Any] | None:
        """Получает глобальные настройки квеста."""
        log.debug(f"ScenarioRepositoryORM | action=get_master quest_key='{quest_key}'")
        stmt = select(ScenarioMaster).where(ScenarioMaster.quest_key == quest_key)
        try:
            result = await self.session.execute(stmt)
            obj = result.scalar_one_or_none()
            if obj:
                log.debug(f"ScenarioRepositoryORM | action=get_master status=found quest_key='{quest_key}'")
                return self._to_dict(obj)
            else:
                log.warning(f"ScenarioRepositoryORM | action=get_master status=not_found quest_key='{quest_key}'")
                return None
        except SQLAlchemyError as e:
            log.exception(f"ScenarioRepositoryORM | action=get_master status=failed quest_key='{quest_key}' error={e}")
            return None

    async def upsert_master(self, master_data: dict[str, Any]) -> None:
        """Создает или обновляет мастер-запись квеста."""
        quest_key = master_data.get("quest_key")
        log.debug(f"ScenarioRepositoryORM | action=upsert_master quest_key='{quest_key}'")

        stmt = insert(ScenarioMaster).values(**master_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["quest_key"], set_={k: v for k, v in master_data.items() if k != "quest_key"}
        )

        try:
            await self.session.execute(stmt)
            log.info(f"ScenarioRepositoryORM | action=upsert_master status=success quest_key='{quest_key}'")
        except SQLAlchemyError as e:
            log.exception(
                f"ScenarioRepositoryORM | action=upsert_master status=failed quest_key='{quest_key}' error={e}"
            )
            raise

    # --- 2. Работа с Scenario_Nodes (Table B) ---

    async def get_node(self, quest_key: str, node_key: str) -> dict[str, Any] | None:
        """Получает данные конкретной сцены."""
        log.debug(f"ScenarioRepositoryORM | action=get_node quest='{quest_key}' node='{node_key}'")
        stmt = select(ScenarioNode).where(ScenarioNode.quest_key == quest_key, ScenarioNode.node_key == node_key)
        try:
            result = await self.session.execute(stmt)
            obj = result.scalar_one_or_none()
            if obj:
                return self._to_dict(obj)
            log.debug(f"ScenarioRepositoryORM | action=get_node status=not_found quest='{quest_key}' node='{node_key}'")
            return None
        except SQLAlchemyError as e:
            log.exception(
                f"ScenarioRepositoryORM | action=get_node status=failed quest='{quest_key}' node='{node_key}' error={e}"
            )
            return None

    async def get_nodes_by_pool(self, quest_key: str, pool_tag: str) -> list[dict[str, Any]]:
        """Поиск нод по тегу в массиве tags (JSONB)."""
        log.debug(f"ScenarioRepositoryORM | action=get_nodes_by_pool quest='{quest_key}' pool='{pool_tag}'")
        try:
            stmt = select(ScenarioNode).where(
                ScenarioNode.quest_key == quest_key, ScenarioNode.tags.contains([pool_tag])
            )
            result = await self.session.execute(stmt)
            nodes = [self._to_dict(n) for n in result.scalars().all()]
            log.debug(f"ScenarioRepositoryORM | action=get_nodes_by_pool status=success count={len(nodes)}")
            return nodes
        except SQLAlchemyError as e:
            log.exception(
                f"ScenarioRepositoryORM | action=get_nodes_by_pool status=failed quest='{quest_key}' pool='{pool_tag}' error={e}"
            )
            return []

    async def get_all_quest_nodes(self, quest_key: str) -> list[dict[str, Any]]:
        """Загружает все ноды квеста."""
        log.debug(f"ScenarioRepositoryORM | action=get_all_quest_nodes quest='{quest_key}'")
        stmt = select(ScenarioNode).where(ScenarioNode.quest_key == quest_key)
        try:
            result = await self.session.execute(stmt)
            nodes = [self._to_dict(n) for n in result.scalars().all()]
            log.debug(f"ScenarioRepositoryORM | action=get_all_quest_nodes status=success count={len(nodes)}")
            return nodes
        except SQLAlchemyError as e:
            log.exception(
                f"ScenarioRepositoryORM | action=get_all_quest_nodes status=failed quest='{quest_key}' error={e}"
            )
            return []

    async def upsert_node(self, node_data: dict[str, Any]) -> None:
        """Создает или обновляет ноду."""
        quest_key = node_data.get("quest_key")
        node_key = node_data.get("node_key")
        log.debug(f"ScenarioRepositoryORM | action=upsert_node quest='{quest_key}' node='{node_key}'")

        stmt = insert(ScenarioNode).values(**node_data)
        # Используем явное имя констрейнта для надежности
        stmt = stmt.on_conflict_do_update(
            constraint="uq_quest_node_key",
            set_={k: v for k, v in node_data.items() if k not in ["quest_key", "node_key"]},
        )

        try:
            await self.session.execute(stmt)
            log.info(f"ScenarioRepositoryORM | action=upsert_node status=success quest='{quest_key}' node='{node_key}'")
        except SQLAlchemyError as e:
            log.exception(
                f"ScenarioRepositoryORM | action=upsert_node status=failed quest='{quest_key}' node='{node_key}' error={e}"
            )
            raise

    async def bulk_insert_nodes(self, nodes_data: list[dict[str, Any]]) -> None:
        """
        Массовая вставка нод.
        Предполагается, что старые ноды уже удалены (или это новые данные).
        Использует ON CONFLICT DO NOTHING для безопасности.
        """
        if not nodes_data:
            return

        quest_key = nodes_data[0].get("quest_key", "unknown")
        count = len(nodes_data)
        log.debug(f"ScenarioRepositoryORM | action=bulk_insert_nodes quest='{quest_key}' count={count}")

        stmt = insert(ScenarioNode).values(nodes_data)
        stmt = stmt.on_conflict_do_nothing(constraint="uq_quest_node_key")

        try:
            await self.session.execute(stmt)
            log.info(
                f"ScenarioRepositoryORM | action=bulk_insert_nodes status=success quest='{quest_key}' count={count}"
            )
        except SQLAlchemyError as e:
            log.exception(
                f"ScenarioRepositoryORM | action=bulk_insert_nodes status=failed quest='{quest_key}' error={e}"
            )
            raise

    async def delete_quest_nodes(self, quest_key: str) -> None:
        """Удаляет все ноды квеста (для перезаливки)."""
        log.debug(f"ScenarioRepositoryORM | action=delete_quest_nodes quest='{quest_key}'")
        stmt = delete(ScenarioNode).where(ScenarioNode.quest_key == quest_key)
        try:
            await self.session.execute(stmt)
            log.info(f"ScenarioRepositoryORM | action=delete_quest_nodes status=success quest='{quest_key}'")
        except SQLAlchemyError as e:
            log.exception(
                f"ScenarioRepositoryORM | action=delete_quest_nodes status=failed quest='{quest_key}' error={e}"
            )
            raise

    # --- 3. Работа с Character_Quest_State (Table C) ---

    async def get_active_state(self, char_id: int) -> dict[str, Any] | None:
        """Загружает сохраненное состояние сессии игрока."""
        log.debug(f"ScenarioRepositoryORM | action=get_active_state char_id={char_id}")
        stmt = select(CharacterScenarioState).where(CharacterScenarioState.char_id == char_id)
        try:
            result = await self.session.execute(stmt)
            obj = result.scalar_one_or_none()
            if obj:
                log.debug(f"ScenarioRepositoryORM | action=get_active_state status=found char_id={char_id}")
                return self._to_dict(obj)
            log.debug(f"ScenarioRepositoryORM | action=get_active_state status=not_found char_id={char_id}")
            return None
        except SQLAlchemyError as e:
            log.exception(f"ScenarioRepositoryORM | action=get_active_state status=failed char_id={char_id} error={e}")
            return None

    async def upsert_state(
        self, char_id: int, quest_key: str, node_key: str, context: dict[str, Any], session_id: UUID
    ) -> None:
        """
        Обновление состояния через DELETE + INSERT.
        Это гарантирует уникальность записи для персонажа, независимо от констрейнтов в БД.
        """
        log.debug(
            f"ScenarioRepositoryORM | action=upsert_state char_id={char_id} quest='{quest_key}' node='{node_key}'"
        )
        try:
            # 1. Удаляем старую запись (если есть)
            delete_stmt = delete(CharacterScenarioState).where(CharacterScenarioState.char_id == char_id)
            await self.session.execute(delete_stmt)

            # 2. Вставляем новую
            data = {
                "char_id": char_id,
                "quest_key": quest_key,
                "current_node_key": node_key,
                "context": context,
                "session_id": session_id,
                "updated_at": func.now(),
            }
            insert_stmt = insert(CharacterScenarioState).values(**data)
            await self.session.execute(insert_stmt)

            await self.session.commit()
            log.info(f"ScenarioRepositoryORM | action=upsert_state status=success char_id={char_id}")
        except SQLAlchemyError as e:
            log.exception(f"ScenarioRepositoryORM | action=upsert_state status=failed char_id={char_id} error={e}")
            await self.session.rollback()
            raise

    async def delete_state(self, char_id: int) -> None:
        """Удаляет запись о состоянии."""
        log.debug(f"ScenarioRepositoryORM | action=delete_state char_id={char_id}")
        stmt = delete(CharacterScenarioState).where(CharacterScenarioState.char_id == char_id)
        try:
            await self.session.execute(stmt)
            await self.session.commit()
            log.info(f"ScenarioRepositoryORM | action=delete_state status=success char_id={char_id}")
        except SQLAlchemyError as e:
            log.exception(f"ScenarioRepositoryORM | action=delete_state status=failed char_id={char_id} error={e}")
            await self.session.rollback()
            raise

    def _to_dict(self, obj: Any) -> dict[str, Any]:
        """Безопасное преобразование ORM-объекта в словарь."""
        if not obj:
            return {}
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_sa_")}
