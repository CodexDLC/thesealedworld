# backend/domains/user_features/scenario/handlers/handler_registry.py

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.domains.user_features.scenario.service.session_service import ScenarioSessionService

from .base_handler import BaseScenarioHandler
from .tutorial_handler import TutorialScenarioHandler

# Словарь специфичных обработчиков
_HANDLERS: dict[str, type[BaseScenarioHandler]] = {
    "awakening_rift": TutorialScenarioHandler,
    # Сюда добавлять новые квесты
}


def get_handler(
    quest_key: str, scenario_service: ScenarioSessionService, db_session: AsyncSession
) -> BaseScenarioHandler | None:
    """
    Фабричный метод.
    Возвращает специфичный обработчик для сценария.
    Если обработчик не найден, возвращает None.
    """
    handler_class = _HANDLERS.get(quest_key)

    if not handler_class:
        return None

    # Инъекция зависимостей (только сервис и сессия БД)
    return handler_class(scenario_service, db_session)
