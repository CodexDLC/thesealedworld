from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_db
from src.backend.features.auth.dependencies import get_current_user
from src.backend.features.auth.models import User
from src.backend.features.game_lobby.dependencies import get_character_creation_service, get_game_lobby_service
from src.backend.features.game_lobby.dto.creation import CreateCharacterRequestDTO, ScenarioPlaceholderPayloadDTO
from src.backend.features.game_lobby.dto.lobby import GameLobbyPayloadDTO
from src.backend.features.game_lobby.services.character_creation_service import CharacterCreationService
from src.backend.features.game_lobby.services.lobby_service import GameLobbyService
from src.shared.enums import CoreDomain
from src.shared.schemas import CoreResponseDTO, GameStateHeader

router = APIRouter(prefix="/game-lobby", tags=["Game Lobby"])


@router.get("/view", response_model=CoreResponseDTO[GameLobbyPayloadDTO])
async def get_lobby_view(
    current_user: Annotated[User, Depends(get_current_user)],
    lobby_service: Annotated[GameLobbyService, Depends(get_game_lobby_service)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
) -> CoreResponseDTO[GameLobbyPayloadDTO]:
    payload = await lobby_service.get_start_payload(current_user, db_session)
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.LOBBY),
        payload=payload,
        payload_type="lobby_start",
    )


@router.post("/start", response_model=CoreResponseDTO[ScenarioPlaceholderPayloadDTO | dict])
async def start_lobby_flow(
    dto: CreateCharacterRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    creation_service: Annotated[CharacterCreationService, Depends(get_character_creation_service)],
) -> CoreResponseDTO[ScenarioPlaceholderPayloadDTO | dict]:
    payload = await creation_service.create_and_enter(current_user, dto)
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.SCENARIO, previous_state=CoreDomain.LOBBY),
        payload=payload,
        payload_type="scenario_placeholder",
    )
