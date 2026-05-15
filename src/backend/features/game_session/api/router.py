from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from src.backend.core.auth import User, get_current_user, require_game_character_scope
from src.backend.features.game_session.dependencies import get_game_session_service
from src.backend.features.game_session.services import GameSessionService
from src.shared.schemas import CoreResponseDTO, EnterCharacterRequestDTO, StateTransitionDTO

router = APIRouter(prefix="/game-session", tags=["Game Session"])


@router.post("/enter", response_model=CoreResponseDTO[StateTransitionDTO | dict[str, Any]])
async def enter_game_session(
    request: Request,
    dto: EnterCharacterRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> CoreResponseDTO[StateTransitionDTO | dict[str, Any]]:
    """Enter the current game session for a character."""
    require_game_character_scope(request, current_user, dto.character_id)
    response = await service.enter_character(current_user, dto.character_id)
    return response


@router.post("/respawn", response_model=CoreResponseDTO[StateTransitionDTO | dict[str, Any]])
async def respawn_character(
    request: Request,
    dto: EnterCharacterRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> CoreResponseDTO[StateTransitionDTO | dict[str, Any]]:
    require_game_character_scope(request, current_user, dto.character_id)
    return await service.respawn_character(current_user, dto.character_id)
