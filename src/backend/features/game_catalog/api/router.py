from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_db
from src.backend.features.game_catalog.dto import GameCatalogBootstrapDTO
from src.backend.features.game_catalog.services import GameCatalogBootstrapService
from src.backend.features.monsters.repositories import MonsterGenerationRepository
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


@router.get("/public/monsters", response_model=dict[str, dict[str, Any]])
async def get_public_monster_catalog(
    service: Annotated[GameCatalogBootstrapService, Depends(get_game_catalog_service)],
) -> dict[str, dict[str, Any]]:
    return service.build_monster_families_catalog()


@router.get("/public/generated-monster-clans", response_model=list[dict[str, Any]])
async def get_public_generated_monster_clans(
    service: Annotated[GameCatalogBootstrapService, Depends(get_game_catalog_service)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    clans = await MonsterGenerationRepository(db_session).list_generated_clans()
    return service.project_generated_monster_clans(clans)
