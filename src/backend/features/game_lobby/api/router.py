from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends

from src.backend.config.settings import settings
from src.backend.features.character.dependencies import get_character_status_service
from src.backend.features.character.services.status_service import CharacterStatusService
from src.backend.features.game_lobby.dependencies import (
    get_character_creation_service,
    get_game_lobby_service,
)
from src.backend.features.game_lobby.services.character_creation_service import CharacterCreationService
from src.backend.features.game_lobby.services.lobby_service import GameLobbyService
from src.backend.features_site.auth.dependencies import get_current_user
from src.backend.features_site.auth.models import User
from src.shared.enums import CoreDomain
from src.shared.schemas import (
    CharacterStatusDTO,
    CoreResponseDTO,
    CreateCharacterRequestDTO,
    DeleteCharacterRequestDTO,
    EnterCharacterRequestDTO,
    GameLobbyPayloadDTO,
    GameStateHeader,
    ScenarioPayloadDTO,
)
from src.shared.utils.dev_utils import log_debug_payload

router = APIRouter(prefix="/game-lobby", tags=["Game Lobby"])


@router.get("/status", response_model=CharacterStatusDTO)
async def get_character_status(
    char_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    status_service: Annotated[CharacterStatusService, Depends(get_character_status_service)],
) -> CharacterStatusDTO:
    """Compatibility wrapper for the character-status status endpoint."""
    return await status_service.get_status(current_user, char_id)


@router.get("/view", response_model=CoreResponseDTO[GameLobbyPayloadDTO])
async def get_lobby_view(
    current_user: Annotated[User, Depends(get_current_user)],
    lobby_service: Annotated[GameLobbyService, Depends(get_game_lobby_service)],
) -> CoreResponseDTO[GameLobbyPayloadDTO]:
    """Returns the main lobby view with character slots."""
    payload = await lobby_service.get_start_payload(current_user)
    response: CoreResponseDTO[GameLobbyPayloadDTO] = CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.LOBBY),
        payload=payload,
        payload_type="lobby_start",
    )
    log_debug_payload("game_lobby.view", response, enabled=settings.debug)
    return response


@router.post("/start", response_model=CoreResponseDTO[ScenarioPayloadDTO | dict[Any, Any]])
async def start_lobby_flow(
    dto: CreateCharacterRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    creation_service: Annotated[CharacterCreationService, Depends(get_character_creation_service)],
) -> CoreResponseDTO[ScenarioPayloadDTO | dict[Any, Any]]:
    """Creates a new character and enters the starting scenario."""
    payload = await creation_service.create_and_enter(current_user, dto)
    response: CoreResponseDTO[ScenarioPayloadDTO | dict[Any, Any]] = CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.SCENARIO, previous_state=CoreDomain.LOBBY),
        payload=payload,
        payload_type="scenario_screen",
    )
    log_debug_payload("game_lobby.start", response, enabled=settings.debug)
    return response


@router.post("/enter", response_model=CoreResponseDTO[ScenarioPayloadDTO | dict[str, Any]])
async def enter_lobby_character(
    dto: EnterCharacterRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    lobby_service: Annotated[GameLobbyService, Depends(get_game_lobby_service)],
) -> CoreResponseDTO[ScenarioPayloadDTO | dict[str, Any]]:
    """Cold lobby enter: rebuilds AC from Postgres before the runtime game session starts."""
    res = await lobby_service.enter_character(current_user, dto.character_id)
    response = cast("CoreResponseDTO[ScenarioPayloadDTO | dict[str, Any]]", res)
    log_debug_payload("game_lobby.enter", response, enabled=settings.debug)
    return response


@router.post("/release", response_model=CoreResponseDTO[dict[str, Any]])
async def release_lobby_character(
    dto: EnterCharacterRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    lobby_service: Annotated[GameLobbyService, Depends(get_game_lobby_service)],
) -> CoreResponseDTO[dict[str, Any]]:
    """Saves the active AC snapshot and removes the runtime AC before returning to lobby."""
    response = await lobby_service.release_character(current_user, dto.character_id)
    log_debug_payload("game_lobby.release", response, enabled=settings.debug)
    return response


@router.post("/delete", response_model=CoreResponseDTO[GameLobbyPayloadDTO])
async def delete_lobby_character(
    dto: DeleteCharacterRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    lobby_service: Annotated[GameLobbyService, Depends(get_game_lobby_service)],
) -> CoreResponseDTO[GameLobbyPayloadDTO]:
    """Deletes a character and cleans up all associated runtime and persistent state."""
    await lobby_service.delete_character(current_user, dto.character_id)

    payload = await lobby_service.get_start_payload(current_user)
    response = CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.LOBBY),
        payload=payload,
        payload_type="lobby_start",
    )
    log_debug_payload("game_lobby.delete", response, enabled=settings.debug)
    return response
