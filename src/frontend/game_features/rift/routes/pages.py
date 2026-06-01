from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, RedirectResponse

from src.frontend.config.settings import settings
from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.game_features.rift.dependencies import (
    get_backend_character_status_api,
    get_backend_inventory_api,
    get_backend_rift_api,
    get_backend_rift_dev_api,
)
from src.frontend.game_features.rift.view_models.screen import (
    build_rift_context,
    build_rift_status_seed,
    has_rift_inventory_runtime_ref,
)
from src.frontend.game_features.session.dependencies import get_session_context_builder
from src.frontend.game_features.session.services.session_context_builder import SessionContextBuilder
from src.frontend.game_features.session.token_state import require_game_access_token
from src.frontend.integrations.backend_api.character_status import BackendCharacterStatusApi
from src.frontend.integrations.backend_api.inventory import BackendInventoryApi
from src.frontend.integrations.backend_api.rift import BackendRiftApi
from src.frontend.integrations.backend_api.rift_dev import BackendRiftDevApi
from src.shared.enums import CoreDomain

router = APIRouter(tags=["Rift"])


@router.get("/testrift", name="test_rift")
async def test_rift(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    rift_api: Annotated[BackendRiftDevApi, Depends(get_backend_rift_dev_api)],
    rift_instance_id: Annotated[str | None, Query()] = None,
    assembly_preset_key: Annotated[str | None, Query()] = None,
):
    if not settings.enable_dev_rift_routes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if not rift_instance_id:
        started_rift = await rift_api.start_starter_rift(assembly_preset_key=assembly_preset_key)
        started_rift_id = str(dict(started_rift.get("meta") or {}).get("rift_instance_id") or "")
        if started_rift_id:
            preset_query = f"&assembly_preset_key={quote(assembly_preset_key, safe='')}" if assembly_preset_key else ""
            return RedirectResponse(
                url=f"/testrift?rift_instance_id={quote(started_rift_id, safe='')}{preset_query}",
                status_code=303,
            )
        rift = started_rift
    else:
        rift = await rift_api.screen(rift_instance_id)
    context = build_rift_context(rift)
    return await ui.render("game/testrift.html", context=context)


@router.post("/game/rift/move", name="game_rift_move")
async def game_rift_move(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    rift_api: Annotated[BackendRiftDevApi, Depends(get_backend_rift_dev_api)],
    rift_instance_id: Annotated[str, Form()],
    target_node_id: Annotated[str, Form()],
    char_id: Annotated[int | None, Form()] = None,
):
    rift = await rift_api.move(rift_instance_id, target_node_id=target_node_id)
    context = build_rift_context(rift)
    return await ui.render("game/session_content_inner.html", context=context)


@router.post("/game/rift/travel/start", name="game_rift_travel_start")
async def game_rift_travel_start(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    rift_dev_api: Annotated[BackendRiftDevApi, Depends(get_backend_rift_dev_api)],
    rift_api: Annotated[BackendRiftApi, Depends(get_backend_rift_api)],
    status_api: Annotated[BackendCharacterStatusApi, Depends(get_backend_character_status_api)],
    inventory_api: Annotated[BackendInventoryApi, Depends(get_backend_inventory_api)],
    rift_instance_id: Annotated[str, Form()],
    target_node_id: Annotated[str, Form()],
    char_id: Annotated[int | None, Form()] = None,
):
    if char_id:
        token = require_game_access_token(request)
        response = await rift_api.travel_start(
            token,
            char_id=char_id,
            target_node_id=target_node_id,
        )
        return await _travel_response_json(
            ui,
            response,
            char_id=char_id,
            token=token,
            status_api=status_api,
            inventory_api=inventory_api,
        )
    response = await rift_dev_api.travel_start(rift_instance_id, target_node_id=target_node_id)
    return await _travel_response_json(ui, response)


@router.post("/game/rift/travel/tick", name="game_rift_travel_tick")
async def game_rift_travel_tick(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    rift_dev_api: Annotated[BackendRiftDevApi, Depends(get_backend_rift_dev_api)],
    rift_api: Annotated[BackendRiftApi, Depends(get_backend_rift_api)],
    status_api: Annotated[BackendCharacterStatusApi, Depends(get_backend_character_status_api)],
    inventory_api: Annotated[BackendInventoryApi, Depends(get_backend_inventory_api)],
    rift_instance_id: Annotated[str, Form()],
    travel_id: Annotated[str, Form()],
    force_event: Annotated[str | None, Form()] = None,
    char_id: Annotated[int | None, Form()] = None,
):
    if char_id:
        token = require_game_access_token(request)
        response = await rift_api.travel_tick(
            token,
            char_id=char_id,
            travel_id=travel_id,
            force_event=force_event,
        )
        return await _travel_response_json(
            ui,
            response,
            char_id=char_id,
            token=token,
            status_api=status_api,
            inventory_api=inventory_api,
        )
    response = await rift_dev_api.travel_tick(
        rift_instance_id,
        travel_id=travel_id,
        force_event=force_event,
    )
    return await _travel_response_json(ui, response)


@router.post("/game/rift/action", name="game_rift_action")
async def game_rift_action(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    rift_dev_api: Annotated[BackendRiftDevApi, Depends(get_backend_rift_dev_api)],
    rift_api: Annotated[BackendRiftApi, Depends(get_backend_rift_api)],
    status_api: Annotated[BackendCharacterStatusApi, Depends(get_backend_character_status_api)],
    inventory_api: Annotated[BackendInventoryApi, Depends(get_backend_inventory_api)],
    rift_instance_id: Annotated[str, Form()],
    action_type: Annotated[str, Form()],
    action_id: Annotated[str | None, Form()] = None,
    target_node_id: Annotated[str | None, Form()] = None,
    direction: Annotated[str | None, Form()] = None,
    travel_id: Annotated[str | None, Form()] = None,
    event_key: Annotated[str | None, Form()] = None,
    result: Annotated[str, Form()] = "victory",
    char_id: Annotated[int | None, Form()] = None,
):
    action_payload = {"result": result}
    if travel_id:
        action_payload["travel_id"] = travel_id
    if event_key:
        action_payload["event_key"] = event_key
    token = require_game_access_token(request) if char_id else None
    if char_id:
        response = await rift_api.action(
            token or "",
            char_id=char_id,
            action_type=action_type,
            action_id=action_id,
            target_node_id=target_node_id,
            direction=direction,
            payload=action_payload,
        )
    else:
        response = await rift_dev_api.action(
            rift_instance_id,
            action_type=action_type,
            action_id=action_id,
            target_node_id=target_node_id,
            direction=direction,
            payload=action_payload,
        )
    payload: dict[str, Any] = {
        "action_type": response.get("action_type"),
        "result": response.get("result"),
        "message": response.get("message"),
        "details": response.get("details") or {},
        "granted_flags": response.get("granted_flags") or [],
        "html": None,
    }
    if response.get("screen"):
        context = await _rift_context_for_screen(
            response["screen"],
            char_id=char_id or 0,
            token=token,
            status_api=status_api,
            inventory_api=inventory_api,
        )
        rendered = await ui.render("game/session_content_inner.html", context=context)
        payload["html"] = rendered.body.decode("utf-8")
    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse(payload)
    context = await _rift_context_for_screen(
        response.get("screen") or {},
        char_id=char_id or 0,
        token=token,
        status_api=status_api,
        inventory_api=inventory_api,
    )
    return await ui.render(
        "game/session_content_inner.html",
        context=context,
    )


@router.post("/game/rift/combat/enter", name="game_rift_combat_enter")
async def game_rift_combat_enter(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    context_builder: Annotated[SessionContextBuilder, Depends(get_session_context_builder)],
    char_id: Annotated[int, Form()],
    combat_id: Annotated[str, Form()],
):
    require_game_access_token(request)
    context = await context_builder.build(
        request,
        state=CoreDomain.COMBAT,
        char_id=char_id,
        transition_metadata={"combat_id": combat_id, "source": "rift"},
    )
    return await ui.render("game/session_content_inner.html", context=context)


@router.post("/game/rift/complete", name="game_rift_complete")
async def game_rift_complete(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    rift_api: Annotated[BackendRiftApi, Depends(get_backend_rift_api)],
    context_builder: Annotated[SessionContextBuilder, Depends(get_session_context_builder)],
    char_id: Annotated[int, Form()],
):
    token = require_game_access_token(request)
    response = await rift_api.complete(token, char_id=char_id)
    target_state = CoreDomain(response.get("target_state") or CoreDomain.EXPLORATION.value)
    context = await context_builder.build(
        request,
        state=target_state,
        char_id=char_id,
        transition_metadata={
            "source": "rift",
            "rift_exit": response,
        },
    )
    return await ui.render("game/session_content_inner.html", context=context)


@router.post("/game/rift/rebuild", name="game_rift_rebuild")
async def game_rift_rebuild(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    rift_api: Annotated[BackendRiftDevApi, Depends(get_backend_rift_dev_api)],
    rift_instance_id: Annotated[str, Form()],
    seed: Annotated[str | None, Form()] = None,
    void_cells: Annotated[int | None, Form()] = None,
):
    if not settings.enable_dev_rift_routes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    rift = await rift_api.rebuild(
        rift_instance_id,
        seed=seed,
        void_cells=void_cells,
    )
    context = build_rift_context(rift)
    return await ui.render("game/session_content_inner.html", context=context)


async def _travel_response_json(
    ui: UIRenderer,
    response: dict,
    *,
    char_id: int = 0,
    token: str | None = None,
    status_api: BackendCharacterStatusApi | None = None,
    inventory_api: BackendInventoryApi | None = None,
) -> JSONResponse:
    payload = {
        "travel": response.get("travel"),
        "combat_prompt": response.get("combat_prompt"),
        "html": None,
    }
    if response.get("screen"):
        context = await _rift_context_for_screen(
            response["screen"],
            char_id=char_id,
            token=token,
            status_api=status_api,
            inventory_api=inventory_api,
        )
        rendered = await ui.render(
            "game/session_content_inner.html",
            context=context,
        )
        payload["html"] = rendered.body.decode("utf-8")
    return JSONResponse(payload)


async def _rift_context_for_screen(
    screen: dict,
    *,
    char_id: int = 0,
    token: str | None = None,
    status_api: BackendCharacterStatusApi | None = None,
    inventory_api: BackendInventoryApi | None = None,
) -> dict:
    if not char_id or not token or status_api is None or inventory_api is None:
        return build_rift_context(screen, char_id=char_id)

    character_status = await status_api.get_panel(token, char_id=char_id)
    status_seed = build_rift_status_seed(character_status, fallback_char_id=char_id)
    inventory_window = None
    if has_rift_inventory_runtime_ref(character_status):
        inventory_response = await inventory_api.view(token, char_id=char_id)
        inventory_window = inventory_response.payload

    return build_rift_context(
        screen,
        char_id=char_id,
        status_seed=status_seed,
        inventory_window=inventory_window,
        character_status=character_status,
    )
