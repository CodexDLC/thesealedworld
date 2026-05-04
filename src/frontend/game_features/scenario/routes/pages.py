from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request

from src.frontend.config.settings import settings
from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.game_features.scenario.dependencies.providers import get_scenario_page_service
from src.frontend.game_features.scenario.services.scenario_page_service import ScenarioPageService
from src.shared.utils.dev_utils import log_debug_payload

router = APIRouter(tags=["Scenario"])


@router.post("/game/scenario/initialize", name="game_scenario_initialize")
async def game_scenario_initialize(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    scenario_service: Annotated[ScenarioPageService, Depends(get_scenario_page_service)],
    char_id: Annotated[int, Form()],
    quest_key: Annotated[str, Form()],
):
    vm = await scenario_service.initialize(request, char_id=char_id, quest_key=quest_key)
    log_debug_payload("scenario_page.game_scenario_initialize", vm, enabled=settings.debug)
    return await ui.render("game/session.html", context=_session_context(vm))


@router.post("/game/scenario/step", name="game_scenario_step")
async def game_scenario_step(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    scenario_service: Annotated[ScenarioPageService, Depends(get_scenario_page_service)],
    char_id: Annotated[int, Form()],
    action_id: Annotated[str, Form()],
):
    template, context = await scenario_service.step(request, char_id=char_id, action_id=action_id)
    log_debug_payload("scenario_page.game_scenario_step", context, enabled=settings.debug)
    if hasattr(context, "model_dump"):
        return await ui.render(template, context=_session_context(context))
    return await ui.render(template, context=context)


@router.get("/game/scenario/resume/{char_id}", name="game_scenario_resume")
async def game_scenario_resume(
    char_id: int,
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    scenario_service: Annotated[ScenarioPageService, Depends(get_scenario_page_service)],
):
    vm = await scenario_service.resume(request, char_id=char_id)
    log_debug_payload("scenario_page.game_scenario_resume", vm, enabled=settings.debug)
    return await ui.render("game/session.html", context=_session_context(vm))


def _session_context(vm) -> dict:
    return {
        "user": vm.user,
        "scenario": vm.scenario,
        "domain": vm.domain,
        "char_id": vm.extra_data.char_id,
        "transaction_id": vm.transaction_id,
        "background_url": vm.extra_data.background_url,
    }
