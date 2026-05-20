from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.features.auth.services.auth_service import FrontendAuthService
from src.frontend.game_features.game_lobby.dependencies.providers import (
    get_game_lobby_page_service,
)
from src.frontend.game_features.game_lobby.services.lobby_page_service import GameLobbyPageService
from src.frontend.game_features.game_lobby.view_models.lobby import build_lobby_page_vm
from src.frontend.game_features.session.cookies import (
    active_character_id_from_cookie,
    clear_active_character_cookie,
    set_active_character_cookie,
)
from src.frontend.game_features.session.token_state import (
    attach_game_tokens_from_backend_response,
    clear_game_token_cookies,
)
from src.shared.schemas import (
    CharacterNameAvailabilityRequestDTO,
    CreateCharacterRequestDTO,
    DeleteCharacterRequestDTO,
    EnterCharacterRequestDTO,
)
from src.shared.schemas.game_lobby import CharacterCreationGender

router = APIRouter(tags=["Game Lobby"])


@router.get("/game-lobby", name="game_lobby")
async def game_lobby_page(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    lobby_service: Annotated[GameLobbyPageService, Depends(get_game_lobby_page_service)],
):
    user = await auth_service.get_current_user(request)
    if user is None:
        return await ui.render(
            "site/index.html",
            context={"auth_overlay_open": True, "auth_mode": "login"},
        )
    response = await lobby_service.get_view(user)
    lobby = build_lobby_page_vm(response)
    return await ui.render(
        "site/index.html",
        context={"user": user, "lobby": lobby, "lobby_overlay_open": True},
    )


@router.get("/api/game-lobby/status", name="api_game_lobby_status")
async def game_lobby_status(
    request: Request,
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    lobby_service: Annotated[GameLobbyPageService, Depends(get_game_lobby_page_service)],
    char_id: int,
):
    await auth_service.require_current_user(request)
    return await lobby_service.get_status(request, char_id)


@router.get("/game-lobby/name-availability", name="game_lobby_name_availability")
async def game_lobby_name_availability(
    request: Request,
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    lobby_service: Annotated[GameLobbyPageService, Depends(get_game_lobby_page_service)],
    name: str,
):
    user = await auth_service.require_current_user(request)
    return await lobby_service.check_name_availability(user, name)


@router.post("/game-lobby/name-availability", name="game_lobby_name_availability_post")
async def game_lobby_name_availability_post(
    request: Request,
    dto: CharacterNameAvailabilityRequestDTO,
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    lobby_service: Annotated[GameLobbyPageService, Depends(get_game_lobby_page_service)],
):
    user = await auth_service.require_current_user(request)
    return await lobby_service.check_name_availability(user, dto.name)


@router.post("/game-lobby/start", name="game_lobby_start")
async def game_lobby_start(
    request: Request,
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    lobby_service: Annotated[GameLobbyPageService, Depends(get_game_lobby_page_service)],
    name: Annotated[str, Form(min_length=3, max_length=16)],
    gender: Annotated[CharacterCreationGender, Form()],
):
    user = await auth_service.require_current_user(request)
    dto = CreateCharacterRequestDTO(name=name, gender=gender)
    response = await lobby_service.start(user, dto)
    if response.payload is None or not hasattr(response.payload, "node_key"):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Scenario payload is unavailable")
    char_id = _char_id_from_payload(response.payload)
    redirect = _active_session_redirect(char_id)
    attach_game_tokens_from_backend_response(redirect, response)
    return redirect


@router.post("/game-lobby/enter", name="game_lobby_enter")
async def game_lobby_enter(
    request: Request,
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    lobby_service: Annotated[GameLobbyPageService, Depends(get_game_lobby_page_service)],
    character_id: Annotated[int, Form()],
):
    user = await auth_service.require_current_user(request)
    response = await lobby_service.select(user, EnterCharacterRequestDTO(character_id=character_id))
    redirect = _active_session_redirect(character_id)
    attach_game_tokens_from_backend_response(redirect, response)
    return redirect


@router.post("/game-lobby/release", name="game_lobby_release")
async def game_lobby_release(
    request: Request,
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    lobby_service: Annotated[GameLobbyPageService, Depends(get_game_lobby_page_service)],
):
    user = await auth_service.require_current_user(request)
    character_id = active_character_id_from_cookie(request)
    await lobby_service.release(user, EnterCharacterRequestDTO(character_id=character_id))
    return _lobby_redirect()


@router.post("/game-lobby/delete", name="game_lobby_delete")
async def game_lobby_delete(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    lobby_service: Annotated[GameLobbyPageService, Depends(get_game_lobby_page_service)],
    character_id: Annotated[int, Form()],
    confirm_name: Annotated[str, Form(min_length=3, max_length=16)],
):
    user = await auth_service.require_current_user(request)
    response = await lobby_service.delete(
        user,
        DeleteCharacterRequestDTO(character_id=character_id, confirm_name=confirm_name),
    )
    lobby = build_lobby_page_vm(response)
    rendered = await ui.render(
        "site/index.html",
        context={"user": user, "lobby": lobby, "lobby_overlay_open": True},
    )
    clear_active_character_cookie(rendered)
    clear_game_token_cookies(rendered)
    return rendered


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


def _lobby_redirect() -> RedirectResponse:
    response = RedirectResponse("/game-lobby", status_code=status.HTTP_303_SEE_OTHER)
    clear_active_character_cookie(response)
    clear_game_token_cookies(response)
    return response
