from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.features.auth.services.auth_service import FrontendAuthService
from src.frontend.game_features.character_status.dependencies import get_status_panel_service
from src.frontend.game_features.character_status.services.status_panel_service import StatusPanelService

router = APIRouter(tags=["Character Status"])


@router.get("/game/character-status/panel", name="game_character_status_panel")
async def character_status_panel(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    service: Annotated[StatusPanelService, Depends(get_status_panel_service)],
    char_id: Annotated[int, Query()],
):
    await auth_service.require_current_user(request)
    actor_core = await service.get_panel(request, char_id=char_id)
    return await ui.render(
        "game/components/status/main.html",
        context={"char_id": char_id, "character_status": actor_core},
    )


@router.get("/api/game/character-status", name="api_game_character_status")
async def character_status_json(
    request: Request,
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    service: Annotated[StatusPanelService, Depends(get_status_panel_service)],
    char_id: Annotated[int, Query()],
):
    await auth_service.require_current_user(request)
    return await service.get_status(request, char_id=char_id)
