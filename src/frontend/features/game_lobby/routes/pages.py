from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.features.auth.services.auth_service import FrontendAuthService
from src.frontend.features.game_lobby.dependencies.providers import (
    get_game_lobby_page_service,
)
from src.frontend.features.game_lobby.services.lobby_page_service import GameLobbyPageService
from src.frontend.features.game_lobby.view_models.lobby import build_lobby_page_vm
from src.shared.schemas import CreateCharacterRequestDTO, DeleteCharacterRequestDTO, EnterCharacterRequestDTO
from src.shared.schemas.game_lobby import CharacterCreationGender

router = APIRouter(tags=["Game Lobby"])
ACTIVE_CHARACTER_COOKIE = "tbmmorpg_active_character_id"


@router.get("/game-lobby", name="game_lobby")
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
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    lobby_service: Annotated[GameLobbyPageService, Depends(get_game_lobby_page_service)],
    name: Annotated[str, Form(min_length=1, max_length=32)],
    gender: Annotated[CharacterCreationGender, Form()],
):
    await auth_service.require_current_user(request)
    dto = CreateCharacterRequestDTO(name=name, gender=gender)
    response = await lobby_service.start(request, dto)
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


@router.get("/game/session", name="game_session")
async def game_session(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    lobby_service: Annotated[GameLobbyPageService, Depends(get_game_lobby_page_service)],
):
    user = await auth_service.require_current_user(request)
    character_id = _active_character_id_from_cookie(request)
    response = await lobby_service.enter(request, EnterCharacterRequestDTO(character_id=character_id))
    if response.payload is None or not hasattr(response.payload, "node_key"):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Game state is not available yet")
    return await ui.render(
        "game/session.html",
        context={
            "user": user,
            "scenario": response.payload,
            "domain": response.header.current_state,
            "char_id": character_id,
            "transaction_id": response.header.transaction_id,
            "background_url": _background_url_from_payload(response.payload),
        },
        status_code=status.HTTP_200_OK,
    )


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
    lobby = build_lobby_page_vm(response)
    return await ui.render("site/game_lobby/index.html", context={"user": user, "lobby": lobby})


def _char_id_from_payload(payload) -> int:
    extra_data = payload.extra_data or {}
    char_id = int(extra_data.get("char_id", 0))
    if char_id <= 0:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Character id is unavailable")
    return char_id


def _active_character_id_from_cookie(request: Request) -> int:
    raw_value = request.cookies.get(ACTIVE_CHARACTER_COOKIE)
    if raw_value is None:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/game-lobby"})
    try:
        character_id = int(raw_value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/game-lobby"}) from exc
    if character_id <= 0:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/game-lobby"})
    return character_id


def _active_session_redirect(character_id: int) -> RedirectResponse:
    response = RedirectResponse("/game/session", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        ACTIVE_CHARACTER_COOKIE,
        str(character_id),
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return response


def _background_url_from_payload(payload) -> str | None:
    extra_data = getattr(payload, "extra_data", None) or {}
    background_url = extra_data.get("background_url")
    if not background_url:
        return None
    return str(background_url)
