from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, Response, status
from fastapi.responses import RedirectResponse

from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.features.auth.services.auth_service import FrontendAuthService
from src.frontend.game_features.session.cookies import set_active_character_cookie
from src.frontend.game_features.session.services.response_director import ResponseDirector
from src.frontend.game_features.tavern.dependencies import get_response_director, get_tavern_action_service
from src.frontend.game_features.tavern.services import TavernActionService
from src.shared.enums import CoreDomain

router = APIRouter(tags=["Tavern"])


@router.post("/game/tavern/action", name="game_tavern_action")
async def game_tavern_action(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    service: Annotated[TavernActionService, Depends(get_tavern_action_service)],
    director: Annotated[ResponseDirector, Depends(get_response_director)],
    char_id: Annotated[int, Form()],
    action: Annotated[str, Form()],
    screen: Annotated[str | None, Form()] = None,
    tavern_id: Annotated[str | None, Form()] = None,
    service_id: Annotated[str | None, Form()] = None,
    location_id: Annotated[str | None, Form()] = None,
):
    await auth_service.require_current_user(request)
    response = await service.action(
        request,
        char_id=char_id,
        action=action,
        screen=screen,
        tavern_id=tavern_id,
        service_id=service_id,
        location_id=location_id,
    )
    template, context = await director.resolve(
        request,
        response,
        source_state=CoreDomain.TAVERN,
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
