import uuid
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, Request

from src.backend.core.auth import User, get_current_user, require_game_character_scope
from src.backend.core.exceptions import SessionReplacedException
from src.backend.core.game_auth import (
    GameTokenPairDTO,
    GameTokenRefreshRequestDTO,
    create_game_token_pair,
    decode_game_refresh_token,
    refresh_game_token_pair,
    require_internal_service_key,
)
from src.backend.features.character.dependencies import get_character_status_service
from src.backend.features.character.services.status_service import CharacterStatusService
from src.backend.features.game_lobby.dependencies import (
    get_character_creation_service,
    get_game_lobby_service,
)
from src.backend.features.game_lobby.services.character_creation_service import CharacterCreationService
from src.backend.features.game_lobby.services.lobby_service import GameLobbyService
from src.shared.enums import CoreDomain
from src.shared.schemas import (
    CharacterNameAvailabilityDTO,
    CharacterNameAvailabilityRequestDTO,
    CharacterStatusDTO,
    CoreResponseDTO,
    CreateCharacterRequestDTO,
    DeleteCharacterRequestDTO,
    EnterCharacterRequestDTO,
    GameLobbyCharacterCreateRequestDTO,
    GameLobbyCharacterDeleteRequestDTO,
    GameLobbyCharacterReleaseRequestDTO,
    GameLobbyCharacterSelectRequestDTO,
    GameLobbyPayloadDTO,
    GameLobbyPopulationStatsDTO,
    GameLobbyUserContextDTO,
    GameStateHeader,
    ScenarioPayloadDTO,
)
from src.shared.schemas.auth import AuthenticatedUser

router = APIRouter(prefix="/game-lobby", tags=["Game Lobby"])


@router.post("/bootstrap", response_model=CoreResponseDTO[GameLobbyPayloadDTO])
async def bootstrap_lobby_for_site_user(
    user_context: GameLobbyUserContextDTO,
    _service: Annotated[object, Depends(require_internal_service_key)],
    lobby_service: Annotated[GameLobbyService, Depends(get_game_lobby_service)],
) -> CoreResponseDTO[GameLobbyPayloadDTO]:
    """Service-to-service lobby bootstrap for the site frontend."""
    user = AuthenticatedUser(id=user_context.user_id, email=user_context.email)
    payload = await lobby_service.get_start_payload(user)
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.LOBBY),
        payload=payload,
        payload_type="lobby_start",
    )


@router.get("/population-stats", response_model=GameLobbyPopulationStatsDTO)
async def get_lobby_population_stats(
    _service: Annotated[object, Depends(require_internal_service_key)],
    lobby_service: Annotated[GameLobbyService, Depends(get_game_lobby_service)],
) -> GameLobbyPopulationStatsDTO:
    """Service-to-service population counters for site cabinet analytics."""
    return await lobby_service.get_population_stats()


@router.post("/select", response_model=CoreResponseDTO[dict[str, object]])
async def select_lobby_character_for_site_user(
    request: Request,
    dto: GameLobbyCharacterSelectRequestDTO,
    _service: Annotated[object, Depends(require_internal_service_key)],
    lobby_service: Annotated[GameLobbyService, Depends(get_game_lobby_service)],
) -> CoreResponseDTO[dict[str, object]]:
    """Select an owned character and issue game tokens for gameplay API calls."""
    user = AuthenticatedUser(id=dto.user_id, email=dto.email)
    response = await lobby_service.enter_character(user, dto.character_id)
    session_id = uuid.uuid4().hex
    tokens = create_game_token_pair(
        user_id=user.id,
        character_id=dto.character_id,
        session_id=session_id,
    )
    await request.app.state.game_session_lock.claim(dto.character_id, session_id)
    payload = {
        **(response.payload or {}),
        "game_tokens": tokens.model_dump(mode="json"),
    }
    return CoreResponseDTO(header=response.header, payload=payload, payload_type="game_character_selected")


@router.post("/create", response_model=CoreResponseDTO[ScenarioPayloadDTO | dict[Any, Any]])
async def create_lobby_character_for_site_user(
    request: Request,
    dto: GameLobbyCharacterCreateRequestDTO,
    _service: Annotated[object, Depends(require_internal_service_key)],
    creation_service: Annotated[CharacterCreationService, Depends(get_character_creation_service)],
) -> CoreResponseDTO[ScenarioPayloadDTO | dict[Any, Any]]:
    """Create a character for a site user and issue gameplay tokens."""
    user = AuthenticatedUser(id=dto.user_id, email=dto.email)
    payload = await creation_service.create_and_enter(user, dto.character)
    char_id = _char_id_from_payload(payload)
    session_id = uuid.uuid4().hex
    tokens = create_game_token_pair(
        user_id=user.id,
        character_id=char_id,
        session_id=session_id,
    )
    await request.app.state.game_session_lock.claim(char_id, session_id)
    payload.extra_data = {
        **(payload.extra_data or {}),
        "game_tokens": tokens.model_dump(mode="json"),
    }
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.SCENARIO, previous_state=CoreDomain.LOBBY),
        payload=payload,
        payload_type="scenario_screen",
    )


@router.post("/name-availability", response_model=CharacterNameAvailabilityDTO)
async def check_lobby_character_name_for_site_user(
    dto: CharacterNameAvailabilityRequestDTO,
    _service: Annotated[object, Depends(require_internal_service_key)],
    creation_service: Annotated[CharacterCreationService, Depends(get_character_creation_service)],
) -> CharacterNameAvailabilityDTO:
    """Check normalized character-name policy and current availability."""
    return await creation_service.check_name_availability(dto.name)


@router.post("/release-selected", response_model=CoreResponseDTO[dict[str, Any]])
async def release_lobby_character_for_site_user(
    dto: GameLobbyCharacterReleaseRequestDTO,
    _service: Annotated[object, Depends(require_internal_service_key)],
    lobby_service: Annotated[GameLobbyService, Depends(get_game_lobby_service)],
) -> CoreResponseDTO[dict[str, Any]]:
    """Release a selected character using the site user's internal context."""
    user = AuthenticatedUser(id=dto.user_id, email=dto.email)
    return await lobby_service.release_character(user, dto.character.character_id)


@router.post("/delete-character", response_model=CoreResponseDTO[GameLobbyPayloadDTO])
async def delete_lobby_character_for_site_user(
    dto: GameLobbyCharacterDeleteRequestDTO,
    _service: Annotated[object, Depends(require_internal_service_key)],
    lobby_service: Annotated[GameLobbyService, Depends(get_game_lobby_service)],
) -> CoreResponseDTO[GameLobbyPayloadDTO]:
    """Delete a site user's owned character without requiring a gameplay token."""
    user = AuthenticatedUser(id=dto.user_id, email=dto.email)
    await lobby_service.delete_character(
        user,
        dto.character.character_id,
        confirm_name=dto.character.confirm_name,
    )
    payload = await lobby_service.get_start_payload(user)
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.LOBBY),
        payload=payload,
        payload_type="lobby_start",
    )


@router.post("/refresh-token", response_model=GameTokenPairDTO)
async def refresh_game_token(
    request: Request,
    dto: GameTokenRefreshRequestDTO,
    _service: Annotated[object, Depends(require_internal_service_key)],
) -> GameTokenPairDTO:
    # Validate that the refresh token belongs to the currently active session for
    # this character. If a newer login claimed the slot, refuse to mint a new
    # access token so the old device cannot resurrect itself.
    claims = decode_game_refresh_token(dto.refresh_token)
    current_session = await request.app.state.game_session_lock.current(claims.character_id)
    if claims.session_id is None or current_session != claims.session_id:
        raise SessionReplacedException()
    return refresh_game_token_pair(dto.refresh_token)


@router.get("/status", response_model=CharacterStatusDTO)
async def get_character_status(
    request: Request,
    char_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    status_service: Annotated[CharacterStatusService, Depends(get_character_status_service)],
) -> CharacterStatusDTO:
    """Compatibility wrapper for the character-status status endpoint."""
    require_game_character_scope(request, current_user, char_id)
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
    return response


@router.post("/start", response_model=CoreResponseDTO[ScenarioPayloadDTO | dict[Any, Any]])
async def start_lobby_flow(
    request: Request,
    dto: CreateCharacterRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    creation_service: Annotated[CharacterCreationService, Depends(get_character_creation_service)],
) -> CoreResponseDTO[ScenarioPayloadDTO | dict[Any, Any]]:
    """Creates a new character and enters the starting scenario."""
    payload = await creation_service.create_and_enter(current_user, dto)
    char_id = _char_id_from_payload(payload)
    session_id = uuid.uuid4().hex
    tokens = create_game_token_pair(
        user_id=current_user.id,
        character_id=char_id,
        session_id=session_id,
    )
    await request.app.state.game_session_lock.claim(char_id, session_id)
    payload.extra_data = {
        **(payload.extra_data or {}),
        "game_tokens": tokens.model_dump(mode="json"),
    }
    response: CoreResponseDTO[ScenarioPayloadDTO | dict[Any, Any]] = CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.SCENARIO, previous_state=CoreDomain.LOBBY),
        payload=payload,
        payload_type="scenario_screen",
    )
    return response


@router.post("/enter", response_model=CoreResponseDTO[ScenarioPayloadDTO | dict[str, Any]])
async def enter_lobby_character(
    request: Request,
    dto: EnterCharacterRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    lobby_service: Annotated[GameLobbyService, Depends(get_game_lobby_service)],
) -> CoreResponseDTO[ScenarioPayloadDTO | dict[str, Any]]:
    """Cold lobby enter: rebuilds AC from Postgres before the runtime game session starts."""
    require_game_character_scope(request, current_user, dto.character_id)
    res = await lobby_service.enter_character(current_user, dto.character_id)
    response = cast("CoreResponseDTO[ScenarioPayloadDTO | dict[str, Any]]", res)
    return response


@router.post("/release", response_model=CoreResponseDTO[dict[str, Any]])
async def release_lobby_character(
    request: Request,
    dto: EnterCharacterRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    lobby_service: Annotated[GameLobbyService, Depends(get_game_lobby_service)],
) -> CoreResponseDTO[dict[str, Any]]:
    """Saves the active AC snapshot and removes the runtime AC before returning to lobby."""
    require_game_character_scope(request, current_user, dto.character_id)
    response = await lobby_service.release_character(current_user, dto.character_id)
    return response


@router.post("/delete", response_model=CoreResponseDTO[GameLobbyPayloadDTO])
async def delete_lobby_character(
    request: Request,
    dto: DeleteCharacterRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    lobby_service: Annotated[GameLobbyService, Depends(get_game_lobby_service)],
) -> CoreResponseDTO[GameLobbyPayloadDTO]:
    """Deletes a character and cleans up all associated runtime and persistent state."""
    require_game_character_scope(request, current_user, dto.character_id)
    await lobby_service.delete_character(current_user, dto.character_id, confirm_name=dto.confirm_name)

    payload = await lobby_service.get_start_payload(current_user)
    response = CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.LOBBY),
        payload=payload,
        payload_type="lobby_start",
    )
    return response


def _char_id_from_payload(payload: ScenarioPayloadDTO) -> int:
    extra_data = payload.extra_data or {}
    char_id = int(extra_data.get("char_id", 0))
    if char_id <= 0:
        raise RuntimeError("Character creation did not return character id")
    return char_id
