from typing import Annotated, Any

from fastapi import APIRouter, Depends

from src.backend.config.settings import settings
from src.backend.features_site.auth.dependencies import get_current_user
from src.backend.features_site.auth.models import User
from src.backend.features.game_session.dependencies import get_game_session_service
from src.backend.features.game_session.services import GameSessionService
from src.shared.schemas import CoreResponseDTO, EnterCharacterRequestDTO, ScenarioPayloadDTO
from src.shared.utils.dev_utils import log_debug_payload

router = APIRouter(prefix="/game-session", tags=["Game Session"])


@router.post("/enter", response_model=CoreResponseDTO[ScenarioPayloadDTO | dict[str, Any]])
async def enter_game_session(
    dto: EnterCharacterRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> CoreResponseDTO[ScenarioPayloadDTO | dict[str, Any]]:
    """Enter the current game session for a character."""
    response = await service.enter_character(current_user, dto.character_id)
    log_debug_payload("game_session.enter", response, enabled=settings.debug)
    return response
