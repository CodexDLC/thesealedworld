from typing import Annotated

from fastapi import APIRouter, Depends

from src.backend.features.auth.dependencies import get_current_user
from src.backend.features.auth.models import User
from src.backend.features.game_lobby.dependencies import get_game_lobby_service
from src.backend.features.game_lobby.dto.lobby import GameLobbyPayloadDTO
from src.backend.features.game_lobby.services.lobby_service import GameLobbyService
from src.shared.enums import CoreDomain
from src.shared.schemas import CoreResponseDTO, GameStateHeader

router = APIRouter(prefix="/game-lobby", tags=["Game Lobby"])


@router.get("/view", response_model=CoreResponseDTO[GameLobbyPayloadDTO])
async def get_lobby_view(
    current_user: Annotated[User, Depends(get_current_user)],
    lobby_service: Annotated[GameLobbyService, Depends(get_game_lobby_service)],
) -> CoreResponseDTO[GameLobbyPayloadDTO]:
    payload = await lobby_service.get_start_payload(current_user)
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.LOBBY),
        payload=payload,
        payload_type="lobby_start",
    )


@router.post("/start", response_model=CoreResponseDTO[GameLobbyPayloadDTO])
async def start_lobby_flow(
    current_user: Annotated[User, Depends(get_current_user)],
    lobby_service: Annotated[GameLobbyService, Depends(get_game_lobby_service)],
) -> CoreResponseDTO[GameLobbyPayloadDTO]:
    payload = await lobby_service.get_start_payload(current_user)
    payload.message = "Character creation flow is not initialized yet."
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.LOBBY),
        payload=payload,
        payload_type="lobby_start",
    )
