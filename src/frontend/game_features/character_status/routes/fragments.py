from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse

from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.features.auth.services.auth_service import FrontendAuthService
from src.frontend.game_features.character_status.dependencies import get_status_panel_service
from src.frontend.game_features.character_status.services.status_panel_service import StatusPanelService
from src.shared.avatars import AVATAR_CATALOG, get_default_tab

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


@router.get("/game/character-status/vitals", name="game_character_status_vitals")
async def character_status_vitals(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    service: Annotated[StatusPanelService, Depends(get_status_panel_service)],
    char_id: Annotated[int, Query()],
):
    await auth_service.require_current_user(request)
    actor_core = await service.get_panel(request, char_id=char_id)
    return await ui.render(
        "game/components/status/vitals_bars.html",
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


@router.get("/game/character-status/avatar-picker", name="game_avatar_picker_modal")
async def avatar_picker_modal(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    service: Annotated[StatusPanelService, Depends(get_status_panel_service)],
    char_id: Annotated[int, Query()],
):
    await auth_service.require_current_user(request)
    actor_core = await service.get_panel(request, char_id=char_id)
    bio = actor_core.bio if actor_core.bio else {}
    return await ui.render(
        "game/components/status/fragments/avatar_picker_modal.html",
        context={
            "char_id": char_id,
            "current_avatar": bio.get("avatar"),
            "current_gender": bio.get("gender", "male"),
            "default_tab": get_default_tab(bio.get("gender", "male")),
            "avatar_catalog": AVATAR_CATALOG,
        },
    )


@router.post("/game/character-status/avatar-picker", name="game_avatar_picker_apply")
async def avatar_picker_apply(
    request: Request,
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    service: Annotated[StatusPanelService, Depends(get_status_panel_service)],
    char_id: Annotated[int, Form()],
    avatar_url: Annotated[str, Form()],
):
    await auth_service.require_current_user(request)
    await service.update_avatar(request, char_id=char_id, avatar_url=avatar_url)
    response = HTMLResponse('<div id="game-modal-root"></div>')
    response.headers["HX-Trigger"] = "character-status-refresh"
    return response
