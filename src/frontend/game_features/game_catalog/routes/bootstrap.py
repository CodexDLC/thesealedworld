from typing import Annotated

from fastapi import APIRouter, Depends, Request

from src.frontend.game_features.game_catalog.dependencies import get_game_catalog_service
from src.frontend.game_features.game_catalog.services import GameCatalogFrontendService
from src.frontend.site_features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.site_features.auth.services.auth_service import FrontendAuthService

router = APIRouter(tags=["Game Catalog"])


@router.get("/game/catalog/bootstrap", name="game_catalog_bootstrap")
async def game_catalog_bootstrap(
    request: Request,
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    service: Annotated[GameCatalogFrontendService, Depends(get_game_catalog_service)],
) -> dict:
    await auth_service.require_current_user(request)
    return await service.get_bootstrap(request)
