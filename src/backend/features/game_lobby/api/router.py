from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.config.settings import settings
from src.backend.core.database import get_db
from src.backend.features.character.dependencies import get_character_status_service
from src.backend.features.character.services.status_service import CharacterStatusService
from src.backend.features.game_lobby.dependencies import (
    get_character_creation_service,
    get_character_sessions,
    get_game_lobby_service,
    get_scenario_service,
)
from src.backend.features.game_lobby.services.character_creation_service import CharacterCreationService
from src.backend.features.game_lobby.services.lobby_service import GameLobbyService
from src.backend.features.game_session.dependencies import get_game_session_service
from src.backend.features.game_session.services import GameSessionService
from src.backend.features.scenario.services import ScenarioService
from src.backend.features_site.auth.dependencies import get_current_user
from src.backend.features_site.auth.models import User
from src.backend.infrastructure.actor_state.managers.session import (
    CharacterSessionManager,
)
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
    db_session: Annotated[AsyncSession, Depends(get_db)],
    status_service: Annotated[CharacterStatusService, Depends(get_character_status_service)],
) -> CharacterStatusDTO:
    """Compatibility wrapper for the character-status status endpoint."""
    return await status_service.get_status(current_user, char_id, db_session)


@router.get("/view", response_model=CoreResponseDTO[GameLobbyPayloadDTO])
async def get_lobby_view(
    current_user: Annotated[User, Depends(get_current_user)],
    lobby_service: Annotated[GameLobbyService, Depends(get_game_lobby_service)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
) -> CoreResponseDTO[GameLobbyPayloadDTO]:
    """Returns the main lobby view with character slots."""
    payload = await lobby_service.get_start_payload(current_user, db_session)
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


@router.post("/enter", response_model=CoreResponseDTO[ScenarioPayloadDTO | dict[Any, Any]])
async def enter_lobby_character(
    dto: EnterCharacterRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    session_service: Annotated[GameSessionService, Depends(get_game_session_service)],
) -> CoreResponseDTO[ScenarioPayloadDTO | dict[Any, Any]]:
    """Compatibility wrapper for the session-owned game entry endpoint."""
    response = await session_service.enter_character(current_user, dto.character_id)
    log_debug_payload("game_lobby.enter", response, enabled=settings.debug)
    return response


@router.post("/delete", response_model=CoreResponseDTO[GameLobbyPayloadDTO])
async def delete_lobby_character(
    dto: DeleteCharacterRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    lobby_service: Annotated[GameLobbyService, Depends(get_game_lobby_service)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
    character_sessions: Annotated[CharacterSessionManager, Depends(get_character_sessions)],
    scenario_service: Annotated[ScenarioService, Depends(get_scenario_service)],
) -> CoreResponseDTO[GameLobbyPayloadDTO]:
    """Deletes a character and cleans up all associated runtime and persistent state."""
    await lobby_service.delete_character(
        current_user, dto.character_id, db_session, character_sessions, scenario_service
    )

    payload = await lobby_service.get_start_payload(current_user, db_session)
    response = CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.LOBBY),
        payload=payload,
        payload_type="lobby_start",
    )
    log_debug_payload("game_lobby.delete", response, enabled=settings.debug)
    return response
