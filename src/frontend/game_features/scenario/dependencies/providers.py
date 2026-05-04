from typing import Annotated

from fastapi import Depends, Request

from src.frontend.config.settings import settings
from src.frontend.game_features.scenario.services.scenario_page_service import ScenarioPageService
from src.frontend.game_features.session.dependencies import get_session_context_builder
from src.frontend.game_features.session.services.response_director import ResponseDirector
from src.frontend.game_features.session.services.session_context_builder import SessionContextBuilder
from src.frontend.integrations.backend_api.character_status import BackendCharacterStatusApi
from src.frontend.integrations.backend_api.scenario import BackendScenarioApi
from src.frontend.site_features.auth.dependencies.providers import get_backend_http_client


def get_backend_scenario_api(request: Request) -> BackendScenarioApi:
    return BackendScenarioApi(get_backend_http_client(request), base_url=settings.backend_base_url)


def get_backend_character_status_api(request: Request) -> BackendCharacterStatusApi:
    return BackendCharacterStatusApi(get_backend_http_client(request), base_url=settings.backend_base_url)


def get_scenario_page_service(
    api: Annotated[BackendScenarioApi, Depends(get_backend_scenario_api)],
    character_status_api: Annotated[BackendCharacterStatusApi, Depends(get_backend_character_status_api)],
) -> ScenarioPageService:
    return ScenarioPageService(api, character_status_api)


def get_response_director(
    context_builder: Annotated[SessionContextBuilder, Depends(get_session_context_builder)],
) -> ResponseDirector:
    return ResponseDirector(context_builder=context_builder)
