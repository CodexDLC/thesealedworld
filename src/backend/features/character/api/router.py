from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request

from src.backend.core.auth import User, get_current_user, require_game_character_scope
from src.backend.features.character.dependencies import get_character_status_service
from src.backend.features.character.services.status_service import CharacterStatusService
from src.shared.schemas import CharacterStatusDTO
from src.shared.schemas.character_status import CharacterActorCoreDTO

router = APIRouter(prefix="/character-status", tags=["Character Status"])


@router.get("/ac", response_model=CharacterActorCoreDTO)
async def get_actor_core(
    request: Request,
    char_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CharacterStatusService, Depends(get_character_status_service)],
) -> CharacterActorCoreDTO:
    require_game_character_scope(request, current_user, char_id)
    return await service.get_actor_core(current_user, char_id)


@router.get("/panel", response_model=CharacterActorCoreDTO)
async def get_panel_actor_core(
    request: Request,
    char_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CharacterStatusService, Depends(get_character_status_service)],
) -> CharacterActorCoreDTO:
    require_game_character_scope(request, current_user, char_id)
    return await service.get_actor_core(current_user, char_id)


@router.get("/status", response_model=CharacterStatusDTO)
async def get_character_status(
    request: Request,
    char_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CharacterStatusService, Depends(get_character_status_service)],
) -> CharacterStatusDTO:
    require_game_character_scope(request, current_user, char_id)
    return await service.get_status(current_user, char_id)


@router.post("/avatar")
async def update_avatar(
    request: Request,
    char_id: Annotated[int, Body()],
    avatar_url: Annotated[str, Body()],
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CharacterStatusService, Depends(get_character_status_service)],
) -> dict[str, str]:
    require_game_character_scope(request, current_user, char_id)
    await service.update_avatar(char_id, avatar_url)
    return {"status": "ok", "avatar_url": avatar_url}
