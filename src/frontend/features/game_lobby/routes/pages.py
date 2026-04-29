from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.features.auth.services.auth_service import FrontendAuthService
from src.frontend.features.game_lobby.dependencies.providers import get_game_lobby_page_service
from src.frontend.features.game_lobby.services.lobby_page_service import GameLobbyPageService
from src.frontend.features.game_lobby.view_models.lobby import build_lobby_page_vm

router = APIRouter(tags=["Game Lobby"])


@router.get("/game-lobby", name="game_lobby")
@router.get("/play", name="play")
async def game_lobby_page(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    lobby_service: Annotated[GameLobbyPageService, Depends(get_game_lobby_page_service)],
):
    user = await auth_service.require_current_user(request)
    response = await lobby_service.get_view(request)
    lobby = build_lobby_page_vm(response)
    return await ui.render("site/game_lobby/index.html", context={"user": user, "lobby": lobby})


@router.post("/game-lobby/start", name="game_lobby_start")
async def game_lobby_start(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    lobby_service: Annotated[GameLobbyPageService, Depends(get_game_lobby_page_service)],
):
    user = await auth_service.require_current_user(request)
    response = await lobby_service.start(request)
    lobby = build_lobby_page_vm(response)
    return await ui.render(
        "site/game_lobby/index.html",
        context={"user": user, "lobby": lobby},
        status_code=status.HTTP_200_OK,
    )
