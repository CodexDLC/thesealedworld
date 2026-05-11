from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status

from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.game_features.inventory.dependencies import get_backend_inventory_api
from src.frontend.integrations.backend_api.inventory import BackendInventoryApi
from src.frontend.site_features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.site_features.auth.services.auth_service import FrontendAuthService
from src.frontend.site_features.auth.token_state import require_access_token
from src.shared.schemas.inventory import InventoryActionRequestDTO, InventoryWindowDTO

router = APIRouter(tags=["Inventory"])


@router.get("/game/inventory/window", name="game_inventory_window")
async def inventory_window(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    inventory_api: Annotated[BackendInventoryApi, Depends(get_backend_inventory_api)],
    char_id: Annotated[int, Query()],
):
    await auth_service.require_current_user(request)
    token = require_access_token(request)
    response = await inventory_api.view(token, char_id=char_id)
    if response.payload is None:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Inventory payload is unavailable")
    inventory = InventoryWindowDTO.model_validate(response.payload)
    return await ui.render(
        "game/components/inventory/window.html",
        context={"char_id": char_id, "inventory_window": inventory},
    )


@router.post("/game/inventory/action", name="game_inventory_action")
async def inventory_action(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    inventory_api: Annotated[BackendInventoryApi, Depends(get_backend_inventory_api)],
    char_id: Annotated[int, Form()],
    action: Annotated[str, Form()],
    item_id: Annotated[str, Form()],
    slot_id: Annotated[str | None, Form()] = None,
):
    await auth_service.require_current_user(request)
    token = require_access_token(request)
    dto = InventoryActionRequestDTO.model_validate(
        {"char_id": char_id, "action": action, "item_id": item_id, "slot_id": slot_id or None}
    )
    notice: str | None = None
    try:
        response = await inventory_api.action(token, dto)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code not in {status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT}:
            raise
        notice = _inventory_error_notice(exc)
        response = await inventory_api.view(token, char_id=char_id)
    if response.payload is None:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Inventory payload is unavailable")
    inventory = InventoryWindowDTO.model_validate(response.payload)
    return await ui.render(
        "game/components/inventory/window.html",
        context={"char_id": char_id, "inventory_window": inventory, "inventory_notice": notice},
    )


def _inventory_error_notice(exc: httpx.HTTPStatusError) -> str:
    try:
        data = exc.response.json()
    except ValueError:
        return exc.response.text or "Inventory action failed"
    detail = data.get("detail") if isinstance(data, dict) else data
    if isinstance(detail, dict):
        return str(detail.get("message") or detail.get("code") or "Inventory action failed")
    return str(detail or "Inventory action failed")
