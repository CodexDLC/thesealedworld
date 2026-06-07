from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response, status

from src.frontend.config.settings import settings
from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.features.auth.services.auth_service import FrontendAuthService
from src.frontend.game_features.game_lobby.dependencies.providers import get_game_lobby_page_service
from src.frontend.game_features.game_lobby.services.lobby_page_service import GameLobbyPageService
from src.frontend.game_features.session.cookies import active_character_id_from_cookie
from src.frontend.game_features.session.dependencies import get_session_context_builder
from src.frontend.game_features.session.services.session_context_builder import SessionContextBuilder
from src.frontend.game_features.session.token_state import (
    extract_game_tokens,
    get_game_access_token,
    set_game_token_cookies,
)
from src.shared.enums import CoreDomain
from src.shared.schemas import EnterCharacterRequestDTO

router = APIRouter(tags=["Game Session"])


@router.get("/game/keepalive", name="game_keepalive")
async def game_keepalive(
    request: Request,
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
) -> Response:
    """Lightweight endpoint that exists only to prod ``GameTokenRefreshMiddleware``.

    The realtime WS supervisor calls this before retrying a handshake that
    closed with auth failure. The request path matches
    ``GAME_TOKEN_REFRESH_PATH_PREFIXES``, so the middleware will refresh the
    ``tbmmorpg_game_access_token`` cookie via the refresh token (which keeps
    the existing session id) before the response is sent.

    Non-destructive by design: we MUST NOT call ``lobby_service.select`` here,
    because that would mint a new ``session_id`` and overwrite the lock. With
    two tabs (or the supervisor firing twice in quick succession) the result
    was a session-replaced ping-pong that fed itself forever. When the
    refresh path can't recover the session, we just return 401 and let the
    supervisor bail to the lobby after MAX_AUTH_RETRIES.
    """
    user = await auth_service.get_current_user(request)
    if user is None:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        active_character_id_from_cookie(request)
    except HTTPException:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
    # If middleware rotated the access cookie, it stored the new token on
    # request.state — the cookies themselves are attached by the middleware
    # on the way out. If middleware gave up (clear_game_token_cookies flag),
    # return 401 so the supervisor stops retrying.
    if getattr(request.state, "clear_game_token_cookies", False):
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
    if not get_game_access_token(request, allow_site_fallback=False):
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _attach_dev_status_context(
    context: dict,
    *,
    user,
    game_session_api,
) -> None:
    context["user"] = user
    context["access_token"] = get_game_access_token_from_context(context) or context.get("access_token", "")
    if not settings.debug or not getattr(user, "is_superuser", False):
        return
    options = await game_session_api.list_starting_imprints()
    context["dev_status_controls"] = {
        "starter_rift_reset": {
            "action": "/game/dev/starter-rift-reset",
            "imprints": [item.model_dump(mode="json") for item in options.imprints],
        }
    }


def get_game_access_token_from_context(context: dict) -> str:
    value = context.get("access_token")
    return str(value or "")


async def _ensure_game_tokens_for_active_character(
    request: Request,
    *,
    user,
    char_id: int,
    lobby_service: GameLobbyPageService,
    force: bool = False,
) -> dict[str, str] | None:
    """Re-issue game cookies when a gameplay tab only has the site session.

    Older tabs can retain ``tbmmorpg_active_character_id`` while missing the
    HttpOnly game-token cookies required by ``/ws/realtime``. Re-selecting the
    active character through the lobby service is the canonical path that
    claims the realtime session slot and issues fresh game tokens.
    """
    if not force and get_game_access_token(request, allow_site_fallback=False):
        return None

    response = await lobby_service.select(user, EnterCharacterRequestDTO(character_id=char_id))
    tokens = extract_game_tokens(response)
    if not tokens:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Game tokens are unavailable")
    request.state.game_access_token = tokens["access_token"]
    if tokens.get("refresh_token"):
        request.state.game_refresh_token = tokens["refresh_token"]
    return tokens


@router.get("/game/session", name="game_session")
async def game_session(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    context_builder: Annotated[SessionContextBuilder, Depends(get_session_context_builder)],
    lobby_service: Annotated[GameLobbyPageService, Depends(get_game_lobby_page_service)],
):
    user = await auth_service.require_current_user(request)
    char_id = active_character_id_from_cookie(request)
    issued_tokens = await _ensure_game_tokens_for_active_character(
        request,
        user=user,
        char_id=char_id,
        lobby_service=lobby_service,
    )
    context = await context_builder.build_current(request, char_id=char_id)
    context["user"] = user
    context["access_token"] = get_game_access_token(request) or ""
    await _attach_dev_status_context(context, user=user, game_session_api=context_builder.game_session_api)
    rendered = await ui.render("game/session.html", context=context)
    if issued_tokens:
        set_game_token_cookies(
            rendered,
            access_token=issued_tokens["access_token"],
            refresh_token=issued_tokens.get("refresh_token"),
        )
    return rendered


@router.get("/game/session/state/{state}", name="game_session_state")
async def game_session_state(
    state: CoreDomain,
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    context_builder: Annotated[SessionContextBuilder, Depends(get_session_context_builder)],
    lobby_service: Annotated[GameLobbyPageService, Depends(get_game_lobby_page_service)],
    char_id: Annotated[int | None, Query()] = None,
    quest_key: Annotated[str | None, Query()] = None,
):
    user = await auth_service.require_current_user(request)
    active_char_id = char_id if char_id is not None else active_character_id_from_cookie(request)
    issued_tokens = await _ensure_game_tokens_for_active_character(
        request,
        user=user,
        char_id=active_char_id,
        lobby_service=lobby_service,
    )
    context = await context_builder.build(request, state=state, char_id=active_char_id, quest_key=quest_key)
    context["user"] = user
    context["access_token"] = get_game_access_token(request) or ""
    await _attach_dev_status_context(context, user=user, game_session_api=context_builder.game_session_api)
    rendered = await ui.render("game/session.html", context=context)
    if issued_tokens:
        set_game_token_cookies(
            rendered,
            access_token=issued_tokens["access_token"],
            refresh_token=issued_tokens.get("refresh_token"),
        )
    return rendered


@router.post("/game/death/respawn", name="game_death_respawn")
async def game_death_respawn(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    context_builder: Annotated[SessionContextBuilder, Depends(get_session_context_builder)],
    char_id: Annotated[int, Form()],
):
    await auth_service.require_current_user(request)
    context = await context_builder.respawn(request, char_id=char_id)
    return await ui.render("game/session_content_inner.html", context=context)


@router.post("/game/dev/starter-rift-reset", name="game_dev_starter_rift_reset")
async def game_dev_starter_rift_reset(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    context_builder: Annotated[SessionContextBuilder, Depends(get_session_context_builder)],
    char_id: Annotated[int, Form()],
    imprint_key: Annotated[str, Form()],
):
    user = await auth_service.require_current_user(request)
    if not settings.debug or not getattr(user, "is_superuser", False):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    context = await context_builder.dev_reset_starter_rift(request, char_id=char_id, imprint_key=imprint_key)
    context["user"] = user
    context["access_token"] = get_game_access_token(request) or ""
    await _attach_dev_status_context(context, user=user, game_session_api=context_builder.game_session_api)
    return await ui.render("game/session_content_inner.html", context=context)


@router.post("/game/loot/claim-all", name="game_loot_claim_all")
async def game_loot_claim_all(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    context_builder: Annotated[SessionContextBuilder, Depends(get_session_context_builder)],
    char_id: Annotated[int, Form()],
    corpse_ids: Annotated[list[str], Form(default_factory=list)],
):
    await auth_service.require_current_user(request)
    context = await context_builder.claim_loot(request, char_id=char_id, corpse_ids=corpse_ids)
    return await ui.render("game/session_content_inner.html", context=context)
