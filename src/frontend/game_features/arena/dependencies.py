from typing import Annotated

from fastapi import Depends, Request

from src.frontend.config.settings import settings
from src.frontend.game_features.arena.services.arena_action_service import ArenaActionService
from src.frontend.game_features.session.dependencies import get_session_context_builder
from src.frontend.game_features.session.services.response_director import ResponseDirector
from src.frontend.game_features.session.services.session_context_builder import SessionContextBuilder
from src.frontend.integrations.backend_api.arena import BackendArenaApi
from src.frontend.site_features.auth.dependencies.providers import get_backend_http_client


def get_backend_arena_api(request: Request) -> BackendArenaApi:
    return BackendArenaApi(client=get_backend_http_client(request), base_url=settings.backend_base_url)


def get_arena_action_service(
    api: Annotated[BackendArenaApi, Depends(get_backend_arena_api)],
) -> ArenaActionService:
    return ArenaActionService(api=api)


def get_response_director(
    context_builder: Annotated[SessionContextBuilder, Depends(get_session_context_builder)],
) -> ResponseDirector:
    return ResponseDirector(context_builder=context_builder)
