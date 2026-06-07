from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from src.backend.config.settings import settings
from src.backend.core.auth import User, get_current_user, require_game_character_scope
from src.backend.core.game_auth import require_internal_service_key
from src.backend.features.game_session.dependencies import get_game_session_service
from src.backend.features.game_session.services import GameSessionService
from src.shared.schemas import CoreResponseDTO, EnterCharacterRequestDTO, StateTransitionDTO
from src.shared.schemas.game_session import DevStarterRiftResetRequestDTO, StartingImprintOptionsDTO
from src.shared.schemas.loot import LootClaimRequestDTO

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


@router.get("/dev/starting-imprints", response_model=StartingImprintOptionsDTO)
async def list_dev_starting_imprints(
    _service_key: Annotated[object, Depends(require_internal_service_key)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> StartingImprintOptionsDTO:
    if not settings.debug:
        from fastapi import HTTPException

        raise HTTPException(status_code=404)
    return await service.list_starting_imprints()


@router.post("/dev/starter-rift-reset", response_model=CoreResponseDTO[StateTransitionDTO | dict[str, Any]])
async def dev_reset_starter_rift_character(
    request: Request,
    dto: DevStarterRiftResetRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    _service_key: Annotated[object, Depends(require_internal_service_key)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> CoreResponseDTO[StateTransitionDTO | dict[str, Any]]:
    if not settings.debug:
        from fastapi import HTTPException

        raise HTTPException(status_code=404)
    require_game_character_scope(request, current_user, dto.character_id)
    return await service.dev_reset_starter_rift_character(
        current_user,
        character_id=dto.character_id,
        imprint_key=dto.imprint_key,
    )


@router.post("/loot/claim-all", response_model=CoreResponseDTO[StateTransitionDTO | dict[str, Any]])
async def claim_post_combat_loot(
    request: Request,
    dto: LootClaimRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> CoreResponseDTO[StateTransitionDTO | dict[str, Any]]:
    require_game_character_scope(request, current_user, dto.char_id)
    return await service.claim_post_combat_loot(current_user, dto.char_id, dto.corpse_ids)
