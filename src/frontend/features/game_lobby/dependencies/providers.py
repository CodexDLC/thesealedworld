from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request  # noqa: TC002

from src.frontend.config.settings import settings
from src.frontend.features.auth.dependencies.providers import get_backend_http_client
from src.frontend.features.game_lobby.services.lobby_page_service import GameLobbyPageService
from src.frontend.integrations.backend_api.game_lobby import BackendGameLobbyApi

if TYPE_CHECKING:
    import httpx


def get_backend_game_lobby_api(request: Request) -> BackendGameLobbyApi:
    client: httpx.AsyncClient = get_backend_http_client(request)
    return BackendGameLobbyApi(client=client, base_url=settings.backend_base_url)


def get_game_lobby_page_service(request: Request) -> GameLobbyPageService:
    return GameLobbyPageService(api=get_backend_game_lobby_api(request))
