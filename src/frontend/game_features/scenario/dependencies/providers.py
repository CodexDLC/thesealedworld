from typing import Annotated

from fastapi import Depends, Request

from src.frontend.config.settings import settings
from src.frontend.game_features.scenario.services.scenario_page_service import ScenarioPageService
from src.frontend.integrations.backend_api.scenario import BackendScenarioApi


def get_backend_scenario_api(request: Request) -> BackendScenarioApi:
    client = request.app.state.backend_http_client
    return BackendScenarioApi(client, base_url=settings.backend_base_url)


def get_scenario_page_service(
    api: Annotated[BackendScenarioApi, Depends(get_backend_scenario_api)],
) -> ScenarioPageService:
    return ScenarioPageService(api)
