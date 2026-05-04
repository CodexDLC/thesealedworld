# backend/domains/user_features/scenario/service/session_service.py
import json
import uuid
from typing import Any

from loguru import logger as log

from src.backend.database.db_contract.i_scenario_repo import IScenarioRepository

# Correct imports from repositories package
from src.backend.database.postgres.repositories.skill_repo import SkillProgressRepo
from src.backend.database.redis.manager.account_manager import AccountManager
from src.backend.database.redis.manager.scenario_manager import ScenarioManager
from src.backend.database.redis.redis_fields import AccountFields as Af


class ScenarioSessionService:
    """
    Сервис управления сессией сценария.
    Координирует работу между ScenarioManager (Redis), IScenarioRepository (DB) и AccountManager.
    Также выполняет роль фасада для выдачи наград и поиска контента (пока нет отдельных сервисов).
    """

    def __init__(self, scenario_manager: ScenarioManager, account_manager: AccountManager, repo: IScenarioRepository):
        self.sm = scenario_manager
        self.am = account_manager
        self.repo = repo

    # --- Session Lifecycle ---

    async def register_new_session(self, char_id: int, quest_key: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Создает новую сессию.
        """
        session_id = uuid.uuid4()
        session_id_str = str(session_id)

        # 1. Обновляем статус аккаунта (через AccountManager)
        await self.enter_scenario_mode(char_id, quest_key, session_id_str)

        # 2. Обогащаем контекст
        context[Af.SCENARIO_SESSION_ID] = session_id_str
        context["quest_key"] = quest_key
        if "step_counter" not in context:
            context["step_counter"] = 0

        # 3. Сохраняем в Redis (через ScenarioManager)
        await self.sm.save_session_context(char_id, context)

        return context

    async def load_session(self, char_id: int) -> dict[str, Any]:
        """
        Загружает сессию (Redis -> DB Fallback).
        """
        # 1. Redis
        context = await self.sm.get_session_context(char_id)

        # 2. DB Fallback
        if not context:
            log.info(f"SessionService | session_miss char={char_id}. Checking DB backup...")
            db_state = await self.repo.get_active_state(char_id)

            if db_state:
                context = db_state.get("context", {})
                if context:
                    await self.sm.save_session_context(char_id, context)
                    log.success(f"SessionService | session_restored from DB char={char_id}")
            else:
                log.warning(f"SessionService | session_not_found anywhere char={char_id}")

        return context

    async def get_session_context(self, char_id: int) -> dict[str, Any]:
        """Прямое чтение из Redis."""
        return await self.sm.get_session_context(char_id)

    async def save_session_context(self, char_id: int, context: dict[str, Any]):
        """Сохранение в Redis."""
        await self.sm.save_session_context(char_id, context)

    async def clear_session(self, char_id: int):
        """Очистка сессии."""
        await self.sm.clear_session(char_id)

    # --- Static Content (Quest Data) ---

    async def get_node(self, quest_key: str, node_key: str) -> dict[str, Any] | None:
        """Получает ноду (Cache -> DB)."""
        # 1. Cache
        node = await self.sm.get_cached_node(quest_key, node_key)
        if node:
            return node

        # 2. Ensure Cache & Retry
        if await self._ensure_static_cache(quest_key):
            return await self.sm.get_cached_node(quest_key, node_key)

        # 3. DB Direct (Fallback)
        log.warning(f"SessionService | Node miss: {quest_key}/{node_key}. DB Fallback.")
        return await self.repo.get_node(quest_key, node_key)

    async def get_quest_master(self, quest_key: str) -> dict[str, Any] | None:
        """Получает мастер-данные."""
        master = await self.sm.get_cached_master(quest_key)
        if master:
            return master

        if await self._ensure_static_cache(quest_key):
            return await self.sm.get_cached_master(quest_key)

        return await self.repo.get_master(quest_key)

    async def get_nodes_by_pool(self, quest_key: str, pool_tag: str) -> list[dict[str, Any]]:
        """Получает ноды по тегу."""
        if not await self._ensure_static_cache(quest_key):
            return await self.repo.get_nodes_by_pool(quest_key, pool_tag)

        all_data = await self.sm.get_all_cached_data(quest_key)
        candidates = []
        if all_data:
            for k, v in all_data.items():
                if not k.startswith("node:"):
                    continue
                try:
                    node_data = json.loads(v)
                    tags = node_data.get("tags")
                    if tags and isinstance(tags, list) and pool_tag in tags:
                        candidates.append(node_data)
                except (json.JSONDecodeError, TypeError):
                    continue
        return candidates

    async def _ensure_static_cache(self, quest_key: str) -> bool:
        """Загружает квест из БД в Redis."""
        if await self.sm.has_static_cache(quest_key):
            return True

        log.info(f"SessionService | Cache MISS for '{quest_key}'. Loading from DB...")
        master = await self.repo.get_master(quest_key)
        if not master:
            return False

        try:
            nodes = await self.repo.get_all_quest_nodes(quest_key)
        except AttributeError:
            log.error("Repo missing 'get_all_quest_nodes'")
            return False

        await self.sm.cache_quest_static_data(quest_key, master, nodes)
        return True

    # --- Backup (DB) ---

    async def backup_progress(self, char_id: int, quest_key: str, node_key: str, context: dict, session_id: uuid.UUID):
        # TODO: REFACTOR: Use ARQ task for async backup to avoid DB load in request cycle
        await self.repo.upsert_state(char_id, quest_key, node_key, context, session_id)

    async def delete_backup(self, char_id: int):
        # TODO: REFACTOR: Use ARQ task
        await self.repo.delete_state(char_id)

    async def get_session_id(self, char_id: int) -> str | None:
        return await self.am.get_account_field(char_id, Af.SCENARIO_SESSION_ID)

    # --- Account Interaction ---

    async def enter_scenario_mode(self, char_id: int, quest_key: str, session_id: str):
        """
        Переводит аккаунт в режим сценария.
        """
        await self.am.enter_scenario(char_id, session_id, quest_key)

    async def clear_account_state(self, char_id: int):
        """
        Возвращает аккаунт в мир.
        """
        await self.am.leave_scenario(char_id)

    async def update_rewards(self, char_id: int, stats: dict, tokens: dict):
        """
        Обновляет награды (статы, токены).
        """
        # Используем update_account_fields для массового обновления
        updates = {"stats": stats, "tokens": tokens}
        await self.am.update_account_fields(char_id, updates)

    async def transition_to_state(self, char_id: int, state: str):
        """
        Меняет стейт аккаунта с сохранением истории.
        """
        await self.am.transition_to_state(char_id, state)

    async def set_location(self, char_id: int, location_id: str):
        """
        Обновляет локацию.
        """
        await self.am.set_location(char_id, location_id)

    # --- Rewards & Content (Temporary Facade) ---

    async def grant_rewards(self, char_id: int, rewards: dict[str, Any]):
        """
        Выдает награды (предметы, скиллы).
        TODO: REFACTOR: Replace direct Repo usage with InventoryService / SkillService or ARQ tasks.
        Currently using direct DB access via shared session.
        """
        db_session = getattr(self.repo, "session", None)
        if not db_session:
            log.error("SessionService | No DB session for rewards")
            return

        # 1. Items
        items = rewards.get("items", [])
        if items:
            # TODO: Call InventoryService.create_item_from_base(item_key)
            # inv_repo = InventoryRepo(db_session)
            for item_key in items:
                await self._grant_single_item(char_id, item_key, None)

        # 2. Skills
        skills = rewards.get("skills", [])
        if skills:
            skill_repo = SkillProgressRepo(db_session)
            await skill_repo.update_skill_unlocked_state(char_id, skills, True)

    async def _grant_single_item(self, char_id: int, item_key: str, repo: Any):
        """
        Вспомогательный метод для выдачи предмета.
        TODO: Implement via InventoryService after refactoring.
        """
        log.warning(f"SessionService | Grant item '{item_key}' skipped (InventoryService not ready)")
        pass

    async def find_tutorial_monster_id(self, target_loc: str) -> str | None:
        """
        Ищет монстра для туториала и возвращает его ID.
        TODO: Implement via WorldService / EncounterService after refactoring.
        """
        log.warning(f"SessionService | Find monster for '{target_loc}' skipped (EncounterService not ready)")
        return None
