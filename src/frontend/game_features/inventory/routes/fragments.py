from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.game_features.inventory.dependencies import get_backend_inventory_api
from src.frontend.integrations.backend_api.inventory import BackendInventoryApi
from src.frontend.site_features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.site_features.auth.services.auth_service import FrontendAuthService
from src.frontend.site_features.auth.token_state import require_access_token
from src.shared.schemas.inventory import InventoryWindowDTO

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
