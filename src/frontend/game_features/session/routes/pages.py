from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response, status

from src.frontend.config.settings import settings
from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.features.auth.services.auth_service import FrontendAuthService
from src.frontend.game_features.session.cookies import active_character_id_from_cookie
from src.frontend.game_features.session.dependencies import get_session_context_builder
from src.frontend.game_features.session.services.session_context_builder import SessionContextBuilder
from src.frontend.game_features.session.token_state import get_game_access_token
from src.shared.enums import CoreDomain

router = APIRouter(tags=["Game Session"])


@router.get("/game/keepalive", name="game_keepalive")
async def game_keepalive(request: Request) -> Response:
    """Lightweight endpoint that exists only to prod ``GameTokenRefreshMiddleware``.

    The realtime WS supervisor calls this before retrying a handshake that
    closed with auth failure: the request path matches
    ``GAME_TOKEN_REFRESH_PATH_PREFIXES``, so the middleware rotates the
    ``tbmmorpg_game_access_token`` cookie (using the refresh token) before
    the response is sent. The body is intentionally empty — clients only
    care about the rotated Set-Cookie and the 2xx status.
    """
    # ``request`` is unused at the handler level on purpose: token rotation
    # happens in the surrounding middleware. Marker for linters/readers below.
    _ = request
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


@router.get("/game/session", name="game_session")
async def game_session(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    context_builder: Annotated[SessionContextBuilder, Depends(get_session_context_builder)],
):
    user = await auth_service.require_current_user(request)
    char_id = active_character_id_from_cookie(request)
    context = await context_builder.build_current(request, char_id=char_id)
    context["user"] = user
    context["access_token"] = get_game_access_token(request) or ""
    await _attach_dev_status_context(context, user=user, game_session_api=context_builder.game_session_api)
    return await ui.render("game/session.html", context=context)


@router.get("/game/session/state/{state}", name="game_session_state")
async def game_session_state(
    state: CoreDomain,
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    context_builder: Annotated[SessionContextBuilder, Depends(get_session_context_builder)],
    char_id: Annotated[int | None, Query()] = None,
    quest_key: Annotated[str | None, Query()] = None,
):
    user = await auth_service.require_current_user(request)
    active_char_id = char_id if char_id is not None else active_character_id_from_cookie(request)
    context = await context_builder.build(request, state=state, char_id=active_char_id, quest_key=quest_key)
    context["user"] = user
    context["access_token"] = get_game_access_token(request) or ""
    await _attach_dev_status_context(context, user=user, game_session_api=context_builder.game_session_api)
    return await ui.render("game/session.html", context=context)


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
