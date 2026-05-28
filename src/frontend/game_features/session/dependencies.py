from typing import Annotated

from fastapi import Depends, Request

from src.frontend.config.settings import settings
from src.frontend.features.auth.dependencies.providers import get_backend_http_client
from src.frontend.game_features.session.services.session_context_builder import SessionContextBuilder
from src.frontend.integrations.backend_api.arena import BackendArenaApi
from src.frontend.integrations.backend_api.character_status import BackendCharacterStatusApi
from src.frontend.integrations.backend_api.city_services import BackendCityServicesApi
from src.frontend.integrations.backend_api.combat import BackendCombatApi
from src.frontend.integrations.backend_api.exploration import BackendExplorationApi
from src.frontend.integrations.backend_api.game_session import BackendGameSessionApi
from src.frontend.integrations.backend_api.inventory import BackendInventoryApi
from src.frontend.integrations.backend_api.rift import BackendRiftApi
from src.frontend.integrations.backend_api.scenario import BackendScenarioApi


def get_backend_exploration_api(request: Request) -> BackendExplorationApi:
    return BackendExplorationApi(client=get_backend_http_client(request), base_url=settings.backend_base_url)


def get_backend_character_status_api(request: Request) -> BackendCharacterStatusApi:
    return BackendCharacterStatusApi(client=get_backend_http_client(request), base_url=settings.backend_base_url)


def get_backend_arena_api(request: Request) -> BackendArenaApi:
    return BackendArenaApi(client=get_backend_http_client(request), base_url=settings.backend_base_url)


def get_backend_combat_api(request: Request) -> BackendCombatApi:
    return BackendCombatApi(client=get_backend_http_client(request), base_url=settings.backend_base_url)


def get_backend_scenario_api(request: Request) -> BackendScenarioApi:
    return BackendScenarioApi(client=get_backend_http_client(request), base_url=settings.backend_base_url)


def get_backend_city_services_api(request: Request) -> BackendCityServicesApi:
    return BackendCityServicesApi(client=get_backend_http_client(request), base_url=settings.backend_base_url)


def get_backend_game_session_api(request: Request) -> BackendGameSessionApi:
    return BackendGameSessionApi(client=get_backend_http_client(request), base_url=settings.backend_base_url)


def get_backend_inventory_api(request: Request) -> BackendInventoryApi:
    return BackendInventoryApi(client=get_backend_http_client(request), base_url=settings.backend_base_url)


def get_backend_rift_api(request: Request) -> BackendRiftApi:
    return BackendRiftApi(client=get_backend_http_client(request), base_url=settings.backend_base_url)


def get_session_context_builder(
    character_status_api: Annotated[BackendCharacterStatusApi, Depends(get_backend_character_status_api)],
    arena_api: Annotated[BackendArenaApi, Depends(get_backend_arena_api)],
    city_services_api: Annotated[BackendCityServicesApi, Depends(get_backend_city_services_api)],
    combat_api: Annotated[BackendCombatApi, Depends(get_backend_combat_api)],
    exploration_api: Annotated[BackendExplorationApi, Depends(get_backend_exploration_api)],
    scenario_api: Annotated[BackendScenarioApi, Depends(get_backend_scenario_api)],
    game_session_api: Annotated[BackendGameSessionApi, Depends(get_backend_game_session_api)],
    inventory_api: Annotated[BackendInventoryApi, Depends(get_backend_inventory_api)],
    rift_api: Annotated[BackendRiftApi, Depends(get_backend_rift_api)],
) -> SessionContextBuilder:
    return SessionContextBuilder(
        character_status_api=character_status_api,
        arena_api=arena_api,
        city_services_api=city_services_api,
        combat_api=combat_api,
        exploration_api=exploration_api,
        scenario_api=scenario_api,
        game_session_api=game_session_api,
        inventory_api=inventory_api,
        rift_api=rift_api,
    )
