from typing import Annotated

from fastapi import Depends, Request

from src.frontend.config.settings import settings
from src.frontend.features.auth.dependencies.providers import get_backend_http_client
from src.frontend.game_features.city_services.services import CityServiceActionService
from src.frontend.game_features.session.dependencies import get_session_context_builder
from src.frontend.game_features.session.services.response_director import ResponseDirector
from src.frontend.game_features.session.services.session_context_builder import SessionContextBuilder
from src.frontend.integrations.backend_api.city_services import BackendCityServicesApi


def get_backend_city_services_api(request: Request) -> BackendCityServicesApi:
    return BackendCityServicesApi(client=get_backend_http_client(request), base_url=settings.backend_base_url)


def get_city_service_action_service(
    api: Annotated[BackendCityServicesApi, Depends(get_backend_city_services_api)],
) -> CityServiceActionService:
    return CityServiceActionService(api=api)


def get_response_director(
    context_builder: Annotated[SessionContextBuilder, Depends(get_session_context_builder)],
) -> ResponseDirector:
    return ResponseDirector(context_builder=context_builder)
