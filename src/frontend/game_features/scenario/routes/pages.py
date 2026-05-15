from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, Response, status
from fastapi.responses import RedirectResponse

from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.features.auth.services.auth_service import FrontendAuthService
from src.frontend.game_features.scenario.dependencies.providers import get_response_director, get_scenario_page_service
from src.frontend.game_features.scenario.services.scenario_page_service import ScenarioPageService
from src.frontend.game_features.session.cookies import set_active_character_cookie
from src.frontend.game_features.session.services.response_director import ResponseDirector
from src.shared.enums import CoreDomain

router = APIRouter(tags=["Scenario"])


@router.post("/game/scenario/initialize", name="game_scenario_initialize")
async def game_scenario_initialize(
    request: Request,
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    scenario_service: Annotated[ScenarioPageService, Depends(get_scenario_page_service)],
    char_id: Annotated[int, Form()],
    quest_key: Annotated[str, Form()],
):
    await auth_service.require_current_user(request)
    await scenario_service.initialize(request, char_id=char_id, quest_key=quest_key)
    return _session_redirect(request, char_id=char_id)


@router.post("/game/scenario/step", name="game_scenario_step")
async def game_scenario_step(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    scenario_service: Annotated[ScenarioPageService, Depends(get_scenario_page_service)],
    director: Annotated[ResponseDirector, Depends(get_response_director)],
    char_id: Annotated[int, Form()],
    action_id: Annotated[str, Form()],
):
    user = await auth_service.require_current_user(request)
    response = await scenario_service.step(request, char_id=char_id, action_id=action_id)
    template, render_context = await director.resolve(
        request,
        response,
        source_state=CoreDomain.SCENARIO,
        char_id=char_id,
        redirect_transitions=True,
    )
    if template == "__session_redirect__":
        return _session_redirect(request, char_id=char_id)
    render_context["user"] = user
    return await ui.render(template, context=render_context)


@router.get("/game/scenario/resume/{char_id}", name="game_scenario_resume")
async def game_scenario_resume(
    char_id: int,
    request: Request,
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    scenario_service: Annotated[ScenarioPageService, Depends(get_scenario_page_service)],
):
    await auth_service.require_current_user(request)
    await scenario_service.resume(request, char_id=char_id)
    return _session_redirect(request, char_id=char_id)


def _session_redirect(request: Request, *, char_id: int) -> Response:
    if "HX-Request" in request.headers:
        response = Response(status_code=status.HTTP_204_NO_CONTENT)
        response.headers["HX-Redirect"] = "/game/session"
    else:
        response = RedirectResponse("/game/session", status_code=status.HTTP_303_SEE_OTHER)
    set_active_character_cookie(response, char_id)
    return response
