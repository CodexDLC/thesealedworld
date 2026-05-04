# backend/domains/user_features/scenario/handlers/base_handler.py
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.enums.domain_enums import CoreDomain

if TYPE_CHECKING:
    from src.backend.domains.internal_systems.dispatcher.system_dispatcher import SystemDispatcher
    from src.backend.domains.user_features.scenario.service.session_service import ScenarioSessionService


class BaseScenarioHandler(ABC):
    """
    Абстрактный контракт для любого сценария.
    Определяет методы, которые обязан реализовать каждый обработчик квеста.
    """

    def __init__(self, manager: "ScenarioSessionService", db_session: AsyncSession):
        self.manager = manager
        self.db = db_session

    @abstractmethod
    async def on_initialize(
        self, char_id: int, quest_master: dict[str, Any], prev_state: str | None = None, prev_loc: str | None = None
    ) -> dict[str, Any]:
        """
        Логика старта сценария.
        Возвращает готовый контекст.
        """
        pass

    @abstractmethod
    async def on_finalize(
        self, char_id: int, context: dict[str, Any], router: "SystemDispatcher"
    ) -> tuple[CoreDomain, Any]:
        """
        Логика завершения сценария.
        Возвращает кортеж: (Целевой Домен, Payload нового домена).
        """
        pass

    async def _start_pve_combat(
        self,
        router: "SystemDispatcher",
        char_id: int,
        monster_id: str,
        location_id: str,
    ) -> tuple[CoreDomain, Any]:
        """
        Хелпер для запуска стандартного PvE боя.
        1. Создает сессию через CombatEntry (standard_pve).
        2. Получает View через CombatGateway.
        """
        combat_context = {
            "teams": [{"players": [char_id], "monsters": [monster_id]}],
            "location_id": location_id,
        }

        # Шаг 1: Создание сессии
        entry_result = await router.process_action(
            domain=CoreDomain.COMBAT_ENTRY, char_id=char_id, action="standard_pve", context=combat_context
        )

        if not entry_result or not entry_result.get("success"):
            log.error(f"BaseScenarioHandler | Failed to create combat session: {entry_result}")
            # Можно выбросить исключение или вернуть ошибку, но пока логируем

        # Шаг 2: Получение View
        payload = await router.get_initial_view(
            target_state=CoreDomain.COMBAT, char_id=char_id, action="initialize", context=combat_context
        )

        return CoreDomain.COMBAT, payload
