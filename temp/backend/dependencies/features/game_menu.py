from fastapi import Depends

from src.backend.database.redis.manager.account_manager import AccountManager
from src.backend.dependencies.base import get_redis_client
from src.backend.dependencies.internal.dispatcher import SystemDispatcher, SystemDispatcherDep
from src.backend.domains.user_features.game_menu.gateway.menu_gateway import GameMenuGateway
from src.backend.domains.user_features.game_menu.services.game_menu_service import GameMenuService
from src.backend.domains.user_features.game_menu.services.menu_session_service import MenuSessionService


# Redis Manager
def get_account_manager(redis=Depends(get_redis_client)) -> AccountManager:
    """Возвращает менеджер аккаунтов."""
    return AccountManager(redis)


# Services
def get_menu_session_service(account_manager: AccountManager = Depends(get_account_manager)) -> MenuSessionService:
    """Возвращает сервис сессий меню."""
    return MenuSessionService(account_manager)


def get_game_menu_service(
    session: MenuSessionService = Depends(get_menu_session_service),
    dispatcher: SystemDispatcher = Depends(SystemDispatcherDep),  # Используем реальный диспетчер
) -> GameMenuService:
    """Возвращает сервис игрового меню."""
    return GameMenuService(session, dispatcher)


# Gateway
def get_menu_gateway(service: GameMenuService = Depends(get_game_menu_service)) -> GameMenuGateway:
    """Возвращает шлюз игрового меню."""
    return GameMenuGateway(service)
