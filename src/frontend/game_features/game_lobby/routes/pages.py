from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from src.frontend.config.settings import settings
from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.game_features.game_lobby.dependencies.providers import (
    get_game_lobby_page_service,
)
from src.frontend.game_features.game_lobby.services.lobby_page_service import GameLobbyPageService
from src.frontend.game_features.game_lobby.view_models.lobby import build_lobby_page_vm
from src.frontend.game_features.session.cookies import set_active_character_cookie
from src.frontend.site_features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.site_features.auth.services.auth_service import FrontendAuthService
from src.shared.schemas import CreateCharacterRequestDTO, DeleteCharacterRequestDTO
from src.shared.schemas.game_lobby import CharacterCreationGender
from src.shared.utils.dev_utils import log_debug_payload

router = APIRouter(tags=["Game Lobby"])


@router.get("/game-lobby", name="game_lobby")
async def game_lobby_page(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    lobby_service: Annotated[GameLobbyPageService, Depends(get_game_lobby_page_service)],
):
    user = await auth_service.require_current_user(request)
    response = await lobby_service.get_view(request)
    log_debug_payload("game_lobby_page.game_lobby_page", response, enabled=settings.debug)
    lobby = build_lobby_page_vm(response)
    return await ui.render("site/game_lobby/index.html", context={"user": user, "lobby": lobby})


@router.get("/api/game-lobby/status", name="api_game_lobby_status")
async def game_lobby_status(
    request: Request,
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    lobby_service: Annotated[GameLobbyPageService, Depends(get_game_lobby_page_service)],
    char_id: int,
):
    await auth_service.require_current_user(request)
    return await lobby_service.get_status(request, char_id)


@router.post("/game-lobby/start", name="game_lobby_start")
async def game_lobby_start(
    request: Request,
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    lobby_service: Annotated[GameLobbyPageService, Depends(get_game_lobby_page_service)],
    name: Annotated[str, Form(min_length=1, max_length=32)],
    gender: Annotated[CharacterCreationGender, Form()],
):
    await auth_service.require_current_user(request)
    dto = CreateCharacterRequestDTO(name=name, gender=gender)
    response = await lobby_service.start(request, dto)
    log_debug_payload("game_lobby_page.game_lobby_start", response, enabled=settings.debug)
    if response.payload is None or not hasattr(response.payload, "node_key"):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Scenario payload is unavailable")
    char_id = _char_id_from_payload(response.payload)
    return _active_session_redirect(char_id)


@router.post("/game-lobby/enter", name="game_lobby_enter")
async def game_lobby_enter(
    request: Request,
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    character_id: Annotated[int, Form()],
):
    await auth_service.require_current_user(request)
    return _active_session_redirect(character_id)


@router.post("/game-lobby/delete", name="game_lobby_delete")
async def game_lobby_delete(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    lobby_service: Annotated[GameLobbyPageService, Depends(get_game_lobby_page_service)],
    character_id: Annotated[int, Form()],
    confirm_name: Annotated[str, Form(min_length=1, max_length=32)],
):
    user = await auth_service.require_current_user(request)
    response = await lobby_service.delete(
        request,
        DeleteCharacterRequestDTO(character_id=character_id, confirm_name=confirm_name),
    )
    log_debug_payload("game_lobby_page.game_lobby_delete", response, enabled=settings.debug)
    lobby = build_lobby_page_vm(response)
    return await ui.render("site/game_lobby/index.html", context={"user": user, "lobby": lobby})


def _char_id_from_payload(payload) -> int:
    extra_data = payload.extra_data or {}
    char_id = int(extra_data.get("char_id", 0))
    if char_id <= 0:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Character id is unavailable")
    return char_id


def _active_session_redirect(character_id: int) -> RedirectResponse:
    response = RedirectResponse("/game/session", status_code=status.HTTP_303_SEE_OTHER)
    set_active_character_cookie(response, character_id)
    return response
