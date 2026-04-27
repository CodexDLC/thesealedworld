from typing import Annotated

from fastapi import Depends

from src.backend.database.redis.manager.account_manager import AccountManager
from src.backend.dependencies.base import DbSessionDep, RedisContainerDep

# Импортируем правильную зависимость диспетчера
from src.backend.dependencies.internal.dispatcher import SystemDispatcherDep
from src.backend.domains.user_features.account.gateway.lobby_gateway import LobbyGateway
from src.backend.domains.user_features.account.gateway.login_gateway import LoginGateway
from src.backend.domains.user_features.account.gateway.onboarding_gateway import OnboardingGateway

# Gateways
from src.backend.domains.user_features.account.gateway.registration_gateway import RegistrationGateway
from src.backend.domains.user_features.account.services.account_session_service import AccountSessionService
from src.backend.domains.user_features.account.services.lobby_service import LobbyService
from src.backend.domains.user_features.account.services.login_service import LoginService
from src.backend.domains.user_features.account.services.onboarding_service import OnboardingService

# Services
from src.backend.domains.user_features.account.services.registration_service import RegistrationService

# --- 0. Core Account Services (Managers) ---


async def get_account_manager(container: RedisContainerDep) -> AccountManager:
    """Возвращает менеджер аккаунтов."""
    return container.account


AccountManagerDep = Annotated[AccountManager, Depends(get_account_manager)]


async def get_account_session_service(account_manager: AccountManagerDep) -> AccountSessionService:
    """Возвращает сервис сессий аккаунта."""
    return AccountSessionService(account_manager)


AccountSessionServiceDep = Annotated[AccountSessionService, Depends(get_account_session_service)]


# --- 1. Domain Services ---


async def get_registration_service(session: DbSessionDep) -> RegistrationService:
    """Возвращает сервис регистрации."""
    return RegistrationService(session)


RegistrationServiceDep = Annotated[RegistrationService, Depends(get_registration_service)]


async def get_onboarding_service(
    session: DbSessionDep,
    session_service: AccountSessionServiceDep,
    dispatcher: SystemDispatcherDep,  # <--- NEW
) -> OnboardingService:
    """Возвращает сервис онбординга."""
    return OnboardingService(session, session_service, dispatcher)


OnboardingServiceDep = Annotated[OnboardingService, Depends(get_onboarding_service)]


async def get_lobby_service(
    session: DbSessionDep, session_service: AccountSessionServiceDep, onboarding_service: OnboardingServiceDep
) -> LobbyService:
    """Возвращает сервис лобби."""
    return LobbyService(session, session_service, onboarding_service)


LobbyServiceDep = Annotated[LobbyService, Depends(get_lobby_service)]


async def get_login_service(session: DbSessionDep, session_service: AccountSessionServiceDep) -> LoginService:
    """Возвращает сервис логина."""
    return LoginService(session, session_service)


LoginServiceDep = Annotated[LoginService, Depends(get_login_service)]


# --- 2. Gateways ---


async def get_registration_gateway(service: RegistrationServiceDep) -> RegistrationGateway:
    """Возвращает шлюз регистрации."""
    return RegistrationGateway(service)


RegistrationGatewayDep = Annotated[RegistrationGateway, Depends(get_registration_gateway)]


async def get_lobby_gateway(service: LobbyServiceDep) -> LobbyGateway:
    """Возвращает шлюз лобби."""
    return LobbyGateway(service)


LobbyGatewayDep = Annotated[LobbyGateway, Depends(get_lobby_gateway)]


async def get_onboarding_gateway(service: OnboardingServiceDep) -> OnboardingGateway:
    """Возвращает шлюз онбординга."""
    return OnboardingGateway(service)


OnboardingGatewayDep = Annotated[OnboardingGateway, Depends(get_onboarding_gateway)]


async def get_login_gateway(
    service: LoginServiceDep,
    onboarding_gateway: OnboardingGatewayDep,
    dispatcher: SystemDispatcherDep,  # Используем импортированную зависимость
) -> LoginGateway:
    """Возвращает шлюз логина."""
    return LoginGateway(service, onboarding_gateway, dispatcher)


LoginGatewayDep = Annotated[LoginGateway, Depends(get_login_gateway)]
