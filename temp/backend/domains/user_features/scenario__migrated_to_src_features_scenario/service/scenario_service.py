# backend/domains/user_features/scenario/service/scenario_service.py
import uuid
from typing import TYPE_CHECKING, Any

from loguru import logger as log

from src.backend.domains.user_features.scenario.engine.director import ScenarioDirector
from src.backend.domains.user_features.scenario.engine.dispatcher_bridge import ScenarioDispatcherBridge
from src.backend.domains.user_features.scenario.engine.evaluator import ScenarioEvaluator
from src.backend.domains.user_features.scenario.engine.formatter import ScenarioFormatter
from src.backend.domains.user_features.scenario.handlers.handler_registry import get_handler
from src.backend.domains.user_features.scenario.service.session_service import ScenarioSessionService
from src.shared.enums.domain_enums import CoreDomain
from src.shared.schemas.scenario import ScenarioPayloadDTO

if TYPE_CHECKING:
    from src.backend.domains.internal_systems.dispatcher.system_dispatcher import SystemDispatcher


class ScenarioService:
    """
    Основной сервис бизнес-логики сценариев.
    Управляет процессом прохождения квеста.
    Возвращает чистые данные (Payload) или кортеж перехода (Domain, Payload).
    """

    def __init__(
        self,
        scenario_manager: ScenarioSessionService,
        scenario_evaluator: ScenarioEvaluator,
        scenario_director: ScenarioDirector,
        scenario_formatter: ScenarioFormatter,
        bridge: ScenarioDispatcherBridge,  # <--- NEW
    ):
        self.manager = scenario_manager
        self.evaluator = scenario_evaluator
        self.director = scenario_director
        self.formatter = scenario_formatter
        self.bridge = bridge  # <--- NEW

    async def initialize_payload(
        self, char_id: int, quest_key: str, prev_state: str | None = None, prev_loc: str | None = None
    ) -> ScenarioPayloadDTO:
        """Логика инициализации сценария."""
        log.info(f"ScenarioService | action=init char={char_id} quest={quest_key}")

        quest_master = await self.manager.get_quest_master(quest_key)
        if not quest_master:
            raise ValueError(f"Quest {quest_key} not found")

        db_session = getattr(self.manager.repo, "session", None)
        if db_session is None:
            raise ValueError("Database session is not available in ScenarioManager repo")

        handler = get_handler(quest_key, self.manager, db_session)
        if not handler:
            raise ValueError(f"Scenario Handler for '{quest_key}' not found")

        # Генерируем session_id
        session_id = uuid.uuid4()
        quest_master["session_id"] = str(session_id)

        context = await handler.on_initialize(char_id, quest_master, prev_state, prev_loc)
        context["visited_nodes"] = []

        start_node_key = str(context.get("current_node_key"))
        node_data = await self.manager.get_node(quest_key, start_node_key)
        context["visited_nodes"].append(start_node_key)

        # Регистрируем состояние аккаунта
        await self.manager.enter_scenario_mode(char_id, quest_key, str(session_id))

        # Сохраняем в Redis
        await self.manager.save_session_context(char_id, context)

        # Бэкап
        await self.manager.backup_progress(char_id, quest_key, start_node_key, context, session_id)

        actions = self.director.get_available_actions(node_data.get("actions_logic", {}) if node_data else {}, context)

        # Formatter returns ScenarioPayloadDTO directly
        payload = self.formatter.build_dto(node_data or {}, actions, context, quest_master)

        if payload.extra_data is None:
            payload.extra_data = {}
        payload.extra_data["char_id"] = char_id

        return payload

    async def resume_payload(self, char_id: int) -> ScenarioPayloadDTO:
        """Логика восстановления сценария."""
        context = await self.manager.load_session(char_id)
        if not context:
            raise ValueError("No session found")

        quest_key = str(context.get("quest_key"))
        node_key = str(context.get("current_node_key"))

        node_data = await self.manager.get_node(quest_key, node_key)
        quest_master = await self.manager.get_quest_master(quest_key)

        actions = self.director.get_available_actions(node_data.get("actions_logic", {}) if node_data else {}, context)

        payload = self.formatter.build_dto(node_data or {}, actions, context, quest_master or {})

        if payload.extra_data is None:
            payload.extra_data = {}
        payload.extra_data["char_id"] = char_id

        return payload

    async def step_payload(
        self, char_id: int, action_id: str, dispatcher: "SystemDispatcher"
    ) -> ScenarioPayloadDTO | tuple[CoreDomain, Any]:
        """
        Логика шага.
        Может вернуть Payload (следующая сцена) или кортеж (Domain, Payload) при финализации.
        """
        context = await self.manager.load_session(char_id)
        if not context:
            raise ValueError(f"Session for char {char_id} not found")

        quest_key = str(context.get("quest_key"))
        current_node_key = str(context.get("current_node_key"))

        # --- ПРОВЕРКА НА FINISH_QUEST ---
        current_node = await self.manager.get_node(quest_key, current_node_key)
        if current_node:
            action_data = current_node.get("actions_logic", {}).get(action_id, {})
            if action_data.get("type") == "finish_quest":
                # Передаем dispatcher в finalize
                return await self.finalize_scenario(char_id, dispatcher)
        # --------------------------------

        new_context, next_node_data = await self.director.execute_step(quest_key, current_node_key, action_id, context)

        new_context["current_node_key"] = next_node_data.get("node_key")
        new_context["total_steps"] = new_context.get("total_steps", 0) + 1

        if "visited_nodes" not in new_context:
            new_context["visited_nodes"] = []

        node_key = next_node_data.get("node_key")
        if node_key and node_key not in new_context["visited_nodes"]:
            new_context["visited_nodes"].append(node_key)

        await self.manager.save_session_context(char_id, new_context)

        # Бэкап каждые 5 шагов или если форсировано
        if new_context["total_steps"] % 5 == 0 or next_node_data.get("force_backup"):
            session_id_str = await self.manager.get_session_id(char_id)
            session_id = uuid.UUID(session_id_str) if session_id_str else uuid.uuid4()
            await self.manager.backup_progress(
                char_id, quest_key, str(new_context["current_node_key"]), new_context, session_id
            )

        quest_master = await self.manager.get_quest_master(quest_key)
        available_actions = self.director.get_available_actions(next_node_data.get("actions_logic", {}), new_context)

        payload = self.formatter.build_dto(next_node_data, available_actions, new_context, quest_master or {})

        if payload.extra_data is None:
            payload.extra_data = {}
        payload.extra_data["char_id"] = char_id

        return payload

    async def finalize_scenario(self, char_id: int, dispatcher: "SystemDispatcher") -> tuple[CoreDomain, Any]:
        """
        Завершение квеста.
        Возвращает кортеж (Целевой Домен, Payload).
        """
        context = await self.manager.get_session_context(char_id)
        if not context:
            raise ValueError(f"Cannot finalize scenario: Session not found for char {char_id}")

        quest_key = str(context.get("quest_key", ""))
        db_session = getattr(self.manager.repo, "session", None)

        if db_session is None:
            raise ValueError("Database session is not available")

        handler = get_handler(quest_key, self.manager, db_session)
        if not handler:
            raise ValueError(f"Handler for {quest_key} not found")

        try:
            # 1. Логика хендлера (награды, статы, переход)
            # Передаем dispatcher в handler
            target_domain, payload = await handler.on_finalize(char_id, context, dispatcher)

            # 2. Очистка (делаем после успешной финализации)
            await self.manager.clear_account_state(char_id)
            await self.manager.clear_session(char_id)
            await self.manager.delete_backup(char_id)

            log.success(f"ScenarioService | char={char_id} quest completed")

            return target_domain, payload

        except Exception as e:
            log.error(f"ScenarioService | finalize_failed char={char_id} error={e}")
            raise
