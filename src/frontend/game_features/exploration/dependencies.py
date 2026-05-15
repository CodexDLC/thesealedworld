from typing import Annotated

from fastapi import Depends, Request

from src.frontend.config.settings import settings
from src.frontend.features.auth.dependencies.providers import get_backend_http_client
from src.frontend.game_features.exploration.services.exploration_action_service import ExplorationActionService
from src.frontend.game_features.session.dependencies import get_session_context_builder
from src.frontend.game_features.session.services.response_director import ResponseDirector
from src.frontend.game_features.session.services.session_context_builder import SessionContextBuilder
from src.frontend.integrations.backend_api.exploration import BackendExplorationApi


def get_backend_exploration_api(request: Request) -> BackendExplorationApi:
    return BackendExplorationApi(client=get_backend_http_client(request), base_url=settings.backend_base_url)


def get_exploration_action_service(
    api: Annotated[BackendExplorationApi, Depends(get_backend_exploration_api)],
) -> ExplorationActionService:
    return ExplorationActionService(api=api)


def get_response_director(
    context_builder: Annotated[SessionContextBuilder, Depends(get_session_context_builder)],
) -> ResponseDirector:
    return ResponseDirector(context_builder=context_builder)
