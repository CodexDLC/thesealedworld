from typing import Annotated

from fastapi import Depends

from src.backend.dependencies.base import RedisContainerDep
from src.backend.dependencies.internal.dispatcher import SystemDispatcherDep
from src.backend.domains.user_features.exploration.engine.dispatcher_bridge import ExplorationDispatcherBridge
from src.backend.domains.user_features.exploration.engine.encounter_engine import EncounterEngine
from src.backend.domains.user_features.exploration.gateway.exploration_gateway import ExplorationGateway
from src.backend.domains.user_features.exploration.services.exploration_service import ExplorationService
from src.backend.domains.user_features.exploration.services.exploration_session_service import ExplorationSessionService

# --- 0. Core Services (Session & Engine) ---


async def get_exploration_session_service(container: RedisContainerDep) -> ExplorationSessionService:
    """
    Создает SessionService, используя менеджеры из RedisContainer.
    """
    return ExplorationSessionService(account_manager=container.account, world_manager=container.world)


ExplorationSessionServiceDep = Annotated[ExplorationSessionService, Depends(get_exploration_session_service)]


async def get_dispatcher_bridge(dispatcher: SystemDispatcherDep) -> ExplorationDispatcherBridge:
    """
    Создает Bridge для межсервисного взаимодействия.
    """
    return ExplorationDispatcherBridge(dispatcher)


ExplorationDispatcherBridgeDep = Annotated[ExplorationDispatcherBridge, Depends(get_dispatcher_bridge)]


async def get_encounter_engine(bridge: ExplorationDispatcherBridgeDep) -> EncounterEngine:
    """
    Создает EncounterEngine с bridge для создания боевых сессий.
    """
    return EncounterEngine(dispatcher_bridge=bridge)


EncounterEngineDep = Annotated[EncounterEngine, Depends(get_encounter_engine)]


# --- 1. Domain Service ---


async def get_exploration_service(
    session: ExplorationSessionServiceDep, engine: EncounterEngineDep, bridge: ExplorationDispatcherBridgeDep
) -> ExplorationService:
    """
    Создает ExplorationService.
    """
    return ExplorationService(session_service=session, encounter_engine=engine, dispatcher_bridge=bridge)


ExplorationServiceDep = Annotated[ExplorationService, Depends(get_exploration_service)]


# --- 2. Gateway ---


async def get_exploration_gateway(service: ExplorationServiceDep) -> ExplorationGateway:
    """
    Создает ExplorationGateway.
    """
    return ExplorationGateway(exploration_service=service)


ExplorationGatewayDep = Annotated[ExplorationGateway, Depends(get_exploration_gateway)]
