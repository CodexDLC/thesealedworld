from typing import Annotated

from fastapi import Depends

from src.backend.database.postgres.repositories.scenario_repository import ScenarioRepositoryORM
from src.backend.dependencies.base import DbSessionDep, RedisContainerDep
from src.backend.dependencies.internal.dispatcher import SystemDispatcherDep
from src.backend.domains.user_features.scenario.engine.director import ScenarioDirector
from src.backend.domains.user_features.scenario.engine.dispatcher_bridge import ScenarioDispatcherBridge
from src.backend.domains.user_features.scenario.engine.evaluator import ScenarioEvaluator
from src.backend.domains.user_features.scenario.engine.formatter import ScenarioFormatter
from src.backend.domains.user_features.scenario.gateway.scenario_gateway import ScenarioGateway
from src.backend.domains.user_features.scenario.service.scenario_service import ScenarioService
from src.backend.domains.user_features.scenario.service.session_service import ScenarioSessionService

# --- 1. Domain Services ---


async def get_scenario_session_service(container: RedisContainerDep, db: DbSessionDep) -> ScenarioSessionService:
    """
    Factory for ScenarioSessionService.
    Uses RedisContainer to access ScenarioManager and AccountManager.
    """
    repo = ScenarioRepositoryORM(db)
    return ScenarioSessionService(scenario_manager=container.scenario, account_manager=container.account, repo=repo)


ScenarioSessionServiceDep = Annotated[ScenarioSessionService, Depends(get_scenario_session_service)]


# --- 2. Engine Components ---


async def get_scenario_evaluator() -> ScenarioEvaluator:
    """Возвращает оценщик сценариев."""
    return ScenarioEvaluator()


ScenarioEvaluatorDep = Annotated[ScenarioEvaluator, Depends(get_scenario_evaluator)]


async def get_scenario_formatter() -> ScenarioFormatter:
    """Возвращает форматтер сценариев."""
    return ScenarioFormatter()


ScenarioFormatterDep = Annotated[ScenarioFormatter, Depends(get_scenario_formatter)]


async def get_scenario_director(
    evaluator: ScenarioEvaluatorDep, session_service: ScenarioSessionServiceDep
) -> ScenarioDirector:
    """Возвращает режиссера сценариев."""
    return ScenarioDirector(evaluator, session_service)


ScenarioDirectorDep = Annotated[ScenarioDirector, Depends(get_scenario_director)]


async def get_scenario_bridge(dispatcher: SystemDispatcherDep) -> ScenarioDispatcherBridge:
    """Возвращает мост диспетчера для сценариев."""
    return ScenarioDispatcherBridge(dispatcher)


ScenarioBridgeDep = Annotated[ScenarioDispatcherBridge, Depends(get_scenario_bridge)]


# --- 3. Main Service ---


async def get_scenario_service(
    session_service: ScenarioSessionServiceDep,
    evaluator: ScenarioEvaluatorDep,
    director: ScenarioDirectorDep,
    formatter: ScenarioFormatterDep,
    bridge: ScenarioBridgeDep,
) -> ScenarioService:
    """Возвращает сервис сценариев."""
    return ScenarioService(session_service, evaluator, director, formatter, bridge=bridge)


ScenarioServiceDep = Annotated[ScenarioService, Depends(get_scenario_service)]


# --- 4. Gateway ---


async def get_scenario_gateway(service: ScenarioServiceDep) -> ScenarioGateway:
    """Возвращает шлюз сценариев."""
    return ScenarioGateway(service)


ScenarioGatewayDep = Annotated[ScenarioGateway, Depends(get_scenario_gateway)]
