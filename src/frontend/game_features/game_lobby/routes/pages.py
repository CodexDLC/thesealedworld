from typing import Annotated
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from src.frontend.config.settings import settings
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
from src.shared.utils.url import build_public_absolute_url

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
        if settings.frontend_surface == "play":
            # Hard exit out of the play subdomain when the session is gone.
            # Redirecting to site /play would have ping-ponged: site sees the still
            # valid access cookie and bounces back here, producing a redirect loop.
            return RedirectResponse(_site_login_expired_url(request), status_code=status.HTTP_303_SEE_OTHER)
        return await ui.render(
            "site/index.html",
            context={"auth_overlay_open": True, "auth_mode": "login"},
        )
    response = await lobby_service.get_view(user)
    lobby = build_lobby_page_vm(response)
    reason = request.query_params.get("reason")
    lobby_notice = "session_replaced" if reason == "session_replaced" else None
    rendered = await ui.render(
        "site/index.html",
        context={
            "user": user,
            "lobby": lobby,
            "lobby_overlay_open": True,
            "lobby_notice": lobby_notice,
            "lobby_close_url": _lobby_close_url(request),
        },
    )
    if lobby_notice == "session_replaced":
        # The browser arrived here because its game tokens were rejected — drop
        # any stale game cookies so a stale device cannot keep hammering the API.
        clear_active_character_cookie(rendered)
        clear_game_token_cookies(rendered)
    return rendered


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
        context={
            "user": user,
            "lobby": lobby,
            "lobby_overlay_open": True,
            "lobby_close_url": _lobby_close_url(request),
        },
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


def _site_play_entry_url(request: Request) -> str:
    return build_public_absolute_url(
        path_or_url="/play",
        configured_base_url=settings.site_base_url or _infer_site_base_url_from_play_request(request),
        request_base_url=str(request.base_url),
    )


def _site_login_expired_url(request: Request) -> str:
    return build_public_absolute_url(
        path_or_url="/login?expired=1",
        configured_base_url=settings.site_base_url or _infer_site_base_url_from_play_request(request),
        request_base_url=str(request.base_url),
    )


def _lobby_close_url(request: Request) -> str:
    return_to = request.query_params.get("return_to", "").strip()
    if _is_safe_site_return_url(request, return_to):
        return return_to
    configured_site = settings.site_base_url or _infer_site_base_url_from_play_request(request)
    return build_public_absolute_url(
        path_or_url="/",
        configured_base_url=configured_site,
        request_base_url=str(request.base_url),
    )


def _is_safe_site_return_url(request: Request, value: str) -> bool:
    if not value:
        return False
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    current_host = request.headers.get("host", "")
    return parsed.netloc != current_host and not (parsed.hostname or "").startswith("play.")


def _infer_site_base_url_from_play_request(request: Request) -> str:
    host = request.headers.get("host", "")
    if host.startswith("play."):
        host = host.removeprefix("play.")
        scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
        return f"{scheme}://{host}"
    return ""
