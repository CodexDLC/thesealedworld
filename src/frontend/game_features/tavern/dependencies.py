from typing import Annotated

from fastapi import Depends, Request

from src.frontend.config.settings import settings
from src.frontend.features.auth.dependencies.providers import get_backend_http_client
from src.frontend.game_features.session.dependencies import get_session_context_builder
from src.frontend.game_features.session.services.response_director import ResponseDirector
from src.frontend.game_features.session.services.session_context_builder import SessionContextBuilder
from src.frontend.game_features.tavern.services import TavernActionService
from src.frontend.integrations.backend_api.tavern import BackendTavernApi


def get_backend_tavern_api(request: Request) -> BackendTavernApi:
    return BackendTavernApi(client=get_backend_http_client(request), base_url=settings.backend_base_url)


def get_tavern_action_service(
    api: Annotated[BackendTavernApi, Depends(get_backend_tavern_api)],
) -> TavernActionService:
    return TavernActionService(api=api)


def get_response_director(
    context_builder: Annotated[SessionContextBuilder, Depends(get_session_context_builder)],
) -> ResponseDirector:
    return ResponseDirector(context_builder=context_builder)
