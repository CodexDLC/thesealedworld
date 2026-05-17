from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, Response, status
from fastapi.responses import RedirectResponse

from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.features.auth.services.auth_service import FrontendAuthService
from src.frontend.game_features.city_services.dependencies import (
    get_city_service_action_service,
    get_response_director,
)
from src.frontend.game_features.city_services.services import CityServiceActionService
from src.frontend.game_features.session.cookies import set_active_character_cookie
from src.frontend.game_features.session.services.response_director import ResponseDirector
from src.shared.enums import CoreDomain

router = APIRouter(tags=["City Services"])


@router.post("/game/city-services/action", name="game_city_service_action")
async def game_city_service_action(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    service: Annotated[CityServiceActionService, Depends(get_city_service_action_service)],
    director: Annotated[ResponseDirector, Depends(get_response_director)],
    char_id: Annotated[int, Form()],
    action: Annotated[str, Form()],
    service_id: Annotated[str, Form()],
    screen: Annotated[str | None, Form()] = None,
    section_id: Annotated[str | None, Form()] = None,
    location_id: Annotated[str | None, Form()] = None,
):
    await auth_service.require_current_user(request)
    response = await service.action(
        request,
        char_id=char_id,
        action=action,
        service_id=service_id,
        screen=screen,
        section_id=section_id,
        location_id=location_id,
    )
    template, context = await director.resolve(
        request,
        response,
        source_state=CoreDomain.CITY_SERVICES,
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
