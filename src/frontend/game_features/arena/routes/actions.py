from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, Request, Response, status
from fastapi.responses import RedirectResponse

from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.game_features.arena.dependencies import get_arena_action_service, get_response_director
from src.frontend.game_features.arena.services import ArenaActionService
from src.frontend.game_features.session.cookies import set_active_character_cookie
from src.frontend.game_features.session.services.response_director import ResponseDirector
from src.frontend.site_features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.site_features.auth.services.auth_service import FrontendAuthService
from src.shared.enums import CoreDomain
from src.shared.schemas.arena import ArenaScreenEnum

router = APIRouter(tags=["Arena"])

ARENA_MODAL_SCREENS = {
    ArenaScreenEnum.MATCH_FOUND.value,
    ArenaScreenEnum.SHADOW_OFFER.value,
    ArenaScreenEnum.COMBAT_PENDING.value,
    ArenaScreenEnum.COMBAT_FAILED.value,
}


@router.post("/game/arena/action", name="game_arena_action")
async def game_arena_action(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    service: Annotated[ArenaActionService, Depends(get_arena_action_service)],
    director: Annotated[ResponseDirector, Depends(get_response_director)],
    char_id: Annotated[int, Form()],
    action: Annotated[str, Form()],
    mode: Annotated[str | None, Form()] = None,
    arena_session_id: Annotated[str | None, Form()] = None,
    wait_limit_sec: Annotated[int | None, Form()] = None,
    confirm: Annotated[bool, Form()] = False,
    modal: Annotated[bool, Form()] = False,
):
    await auth_service.require_current_user(request)
    value: dict[str, Any] = {}
    if arena_session_id:
        value["arena_session_id"] = arena_session_id
    if wait_limit_sec:
        value["wait_limit_sec"] = wait_limit_sec
    if confirm:
        value["confirm"] = True
    response = await service.action(request, char_id=char_id, action=action, mode=mode, value=value)
    template, context = await director.resolve(
        request,
        response,
        source_state=CoreDomain.ARENA,
        char_id=char_id,
        redirect_transitions=True,
    )
    if template == "__session_redirect__":
        return _session_redirect(request, char_id=char_id)
    if modal:
        return await _arena_modal_response(ui, response.payload, char_id=char_id)
    return await ui.render(template, context=context)


def _session_redirect(request: Request, *, char_id: int) -> Response:
    if "HX-Request" in request.headers:
        response = Response(status_code=status.HTTP_204_NO_CONTENT)
        response.headers["HX-Redirect"] = "/game/session"
    else:
        response = RedirectResponse("/game/session", status_code=status.HTTP_303_SEE_OTHER)
    set_active_character_cookie(response, char_id)
    return response


async def _arena_modal_response(ui: UIRenderer, payload: object, *, char_id: int) -> Response:
    screen = getattr(payload, "screen", None)
    screen_value = screen.value if screen is not None and hasattr(screen, "value") else screen
    if screen_value not in ARENA_MODAL_SCREENS:
        return Response('<div id="game-modal-root"></div>', media_type="text/html")
    return await ui.render(
        "game/domains/arena/fragments/confirmation_modal.html",
        context={"arena": payload, "char_id": char_id},
    )


@router.post("/game/arena/group-action", name="game_arena_group_action")
async def game_arena_group_action(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    service: Annotated[ArenaActionService, Depends(get_arena_action_service)],
    char_id: Annotated[int, Form()],
    action: Annotated[str, Form()],
    item_id: Annotated[str | None, Form()] = None,
):
    await auth_service.require_current_user(request)
    response = await service.group_action(request, char_id=char_id, action=action, item_id=item_id)
    payload = response.payload
    notice = {}
    if payload is not None and hasattr(payload, "metadata") and isinstance(payload.metadata, dict):
        notice = payload.metadata.get("group_action", {})
    return await ui.render(
        "game/domains/arena/fragments/group_action_modal.html",
        context={"notice": notice},
    )
