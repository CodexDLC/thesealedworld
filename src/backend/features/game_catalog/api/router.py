from typing import Annotated

from fastapi import APIRouter, Depends

from src.backend.features.game_catalog.dto import GameCatalogBootstrapDTO
from src.backend.features.game_catalog.services import GameCatalogBootstrapService
from src.backend.features_site.auth.dependencies import get_current_user
from src.backend.features_site.auth.models import User

router = APIRouter(prefix="/game/catalog", tags=["Game Catalog"])


def get_game_catalog_service() -> GameCatalogBootstrapService:
    return GameCatalogBootstrapService()


@router.get("/bootstrap", response_model=GameCatalogBootstrapDTO)
async def get_catalog_bootstrap(
    _current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[GameCatalogBootstrapService, Depends(get_game_catalog_service)],
) -> GameCatalogBootstrapDTO:
    return service.build_bootstrap()
