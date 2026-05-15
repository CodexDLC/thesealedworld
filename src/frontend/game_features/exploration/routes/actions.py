from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, Response, status
from fastapi.responses import RedirectResponse

from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.features.auth.services.auth_service import FrontendAuthService
from src.frontend.game_features.exploration.dependencies import (
    get_exploration_action_service,
    get_response_director,
)
from src.frontend.game_features.exploration.services.exploration_action_service import ExplorationActionService
from src.frontend.game_features.session.cookies import set_active_character_cookie
from src.frontend.game_features.session.services.response_director import ResponseDirector
from src.shared.enums import CoreDomain

router = APIRouter(tags=["Exploration"])


@router.post("/game/exploration/move", name="game_exploration_move")
async def game_exploration_move(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    service: Annotated[ExplorationActionService, Depends(get_exploration_action_service)],
    director: Annotated[ResponseDirector, Depends(get_response_director)],
    char_id: Annotated[int, Form()],
    direction: Annotated[str | None, Form()] = None,
    target_id: Annotated[str | None, Form()] = None,
):
    await auth_service.require_current_user(request)
    response = await service.move(request, char_id=char_id, direction=direction, target_id=target_id)
    template, context = await director.resolve(
        request,
        response,
        source_state=CoreDomain.EXPLORATION,
        char_id=char_id,
        redirect_transitions=True,
    )
    if template == "__session_redirect__":
        return _session_redirect(request, char_id=char_id)
    return await ui.render(template, context=context)


@router.post("/game/exploration/interact", name="game_exploration_interact")
async def game_exploration_interact(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    service: Annotated[ExplorationActionService, Depends(get_exploration_action_service)],
    director: Annotated[ResponseDirector, Depends(get_response_director)],
    char_id: Annotated[int, Form()],
    action: Annotated[str, Form()],
    target_id: Annotated[str | None, Form()] = None,
):
    await auth_service.require_current_user(request)
    response = await service.interact(request, char_id=char_id, action=action, target_id=target_id)
    template, context = await director.resolve(
        request,
        response,
        source_state=CoreDomain.EXPLORATION,
        char_id=char_id,
        redirect_transitions=True,
    )
    if template == "__session_redirect__":
        return _session_redirect(request, char_id=char_id)
    return await ui.render(template, context=context)


@router.post("/game/exploration/use-service", name="game_exploration_use_service")
async def game_exploration_use_service(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    service: Annotated[ExplorationActionService, Depends(get_exploration_action_service)],
    director: Annotated[ResponseDirector, Depends(get_response_director)],
    char_id: Annotated[int, Form()],
    service_id: Annotated[str, Form()],
):
    await auth_service.require_current_user(request)
    response = await service.use_service(request, char_id=char_id, service_id=service_id)
    template, context = await director.resolve(
        request,
        response,
        source_state=CoreDomain.EXPLORATION,
        char_id=char_id,
        redirect_transitions=True,
    )
    if template == "__session_redirect__":
        return _session_redirect(request, char_id=char_id)
    return await ui.render(template, context=context)


def _session_redirect(request: Request, *, char_id: int) -> Response:
    if "HX-Request" in request.headers:
        response = Response(status_code=status.HTTP_204_NO_CONTENT)
        response.headers["HX-Redirect"] = "/game/session"
    else:
        response = RedirectResponse("/game/session", status_code=status.HTTP_303_SEE_OTHER)
    set_active_character_cookie(response, char_id)
    return response
