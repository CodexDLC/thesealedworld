from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_db
from src.backend.features.character.dependencies import get_character_status_service
from src.backend.features.character.services.status_service import CharacterStatusService
from src.backend.features_site.auth.dependencies import get_current_user
from src.backend.features_site.auth.models import User
from src.shared.schemas import CharacterStatusDTO
from src.shared.schemas.character_status import CharacterActorCoreDTO

router = APIRouter(prefix="/character-status", tags=["Character Status"])


@router.get("/ac", response_model=CharacterActorCoreDTO)
async def get_actor_core(
    char_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[CharacterStatusService, Depends(get_character_status_service)],
) -> CharacterActorCoreDTO:
    return await service.get_actor_core(current_user, char_id, db_session)


@router.get("/panel", response_model=CharacterActorCoreDTO)
async def get_panel_actor_core(
    char_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[CharacterStatusService, Depends(get_character_status_service)],
) -> CharacterActorCoreDTO:
    return await service.get_actor_core(current_user, char_id, db_session)


@router.get("/status", response_model=CharacterStatusDTO)
async def get_character_status(
    char_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[CharacterStatusService, Depends(get_character_status_service)],
) -> CharacterStatusDTO:
    return await service.get_status(current_user, char_id, db_session)
