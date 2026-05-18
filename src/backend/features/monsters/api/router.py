from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Query

from src.backend.core.database import get_db
from src.backend.features.monsters.dto.generated_view import GeneratedMonstersResponseDTO
from src.backend.features.monsters.repositories import MonsterGenerationRepository
from src.backend.features.monsters.services.generated_view_service import GeneratedMonsterViewService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/admin/monsters", tags=["monsters-admin"])


def get_generated_monster_view_service(
    db_session: Annotated[AsyncSession, Depends(get_db)],
) -> GeneratedMonsterViewService:
    return GeneratedMonsterViewService(MonsterGenerationRepository(db_session))


@router.get("/generated", response_model=GeneratedMonstersResponseDTO)
async def get_generated_monsters(
    service: Annotated[GeneratedMonsterViewService, Depends(get_generated_monster_view_service)],
    family_id: str | None = None,
    clan_id: str | None = None,
    role: str | None = None,
    include_members: bool = True,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> GeneratedMonstersResponseDTO:
    return await service.list_generated(
        family_id=family_id,
        clan_id=clan_id,
        role=role,
        include_members=include_members,
        limit=limit,
        offset=offset,
    )


__all__ = ["get_generated_monster_view_service", "router"]
