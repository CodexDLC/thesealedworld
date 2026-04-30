from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_db
from src.backend.core.exceptions import BusinessLogicException
from src.backend.features.auth.dependencies import get_current_user
from src.backend.features.auth.models import User
from src.backend.features.game_lobby.dependencies import (
    get_character_creation_service,
    get_character_sessions,
    get_game_lobby_service,
    get_scenario_service,
)
from src.backend.features.game_lobby.services.character_creation_service import CharacterCreationService
from src.backend.features.game_lobby.services.lobby_service import GameLobbyService
from src.backend.features.scenario.services import ScenarioService, ScenarioSessionNotFoundError
from src.backend.infrastructure.db.actor_state.models import Character
from src.backend.infrastructure.redis.character_session_manager import CharacterSessionManager
from src.shared.enums import CoreDomain
from src.shared.schemas import (
    CoreResponseDTO,
    CreateCharacterRequestDTO,
    DeleteCharacterRequestDTO,
    EnterCharacterRequestDTO,
    GameLobbyPayloadDTO,
    GameStateHeader,
    ScenarioPayloadDTO,
)

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


@router.post("/start", response_model=CoreResponseDTO[ScenarioPayloadDTO | dict])
async def start_lobby_flow(
    dto: CreateCharacterRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    creation_service: Annotated[CharacterCreationService, Depends(get_character_creation_service)],
) -> CoreResponseDTO[ScenarioPayloadDTO | dict]:
    payload = await creation_service.create_and_enter(current_user, dto)
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.SCENARIO, previous_state=CoreDomain.LOBBY),
        payload=payload,
        payload_type="scenario_screen",
    )


@router.post("/enter", response_model=CoreResponseDTO[ScenarioPayloadDTO | dict])
async def enter_lobby_character(
    dto: EnterCharacterRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
    scenario_service: Annotated[ScenarioService, Depends(get_scenario_service)],
) -> CoreResponseDTO[ScenarioPayloadDTO | dict]:
    character = await _get_owned_character_or_raise(db_session, current_user, dto.character_id)
    char_id = character.character_id
    stage = character.game_stage.upper()

    if stage in {CoreDomain.SCENARIO.value, "SESSION_PENDING", CoreDomain.LOBBY.value}:
        try:
            payload = await scenario_service.resume(char_id)
        except ScenarioSessionNotFoundError:
            payload = await scenario_service.initialize(char_id, "awakening_rift", source="lobby_enter")
            character.game_stage = CoreDomain.SCENARIO.value.lower()
            character.prev_game_stage = CoreDomain.LOBBY.value.lower()
            await db_session.commit()

        payload.extra_data = {
            **(payload.extra_data or {}),
            "char_id": char_id,
            "quest_key": (payload.extra_data or {}).get("quest_key", "awakening_rift"),
        }
        return CoreResponseDTO(
            header=GameStateHeader(current_state=CoreDomain.SCENARIO, previous_state=CoreDomain.LOBBY),
            payload=payload,
            payload_type="scenario_screen",
        )

    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.EXPLORATION, previous_state=CoreDomain.LOBBY),
        payload={
            "character_id": char_id,
            "name": character.name,
            "stage": character.game_stage,
            "message": "Game shell for this state is not implemented yet.",
        },
        payload_type="game_state_unavailable",
    )


@router.post("/delete", response_model=CoreResponseDTO[GameLobbyPayloadDTO])
async def delete_lobby_character(
    dto: DeleteCharacterRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    lobby_service: Annotated[GameLobbyService, Depends(get_game_lobby_service)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
    character_sessions: Annotated[CharacterSessionManager, Depends(get_character_sessions)],
    scenario_service: Annotated[ScenarioService, Depends(get_scenario_service)],
) -> CoreResponseDTO[GameLobbyPayloadDTO]:
    character = await _get_owned_character_or_raise(db_session, current_user, dto.character_id)
    if dto.confirm_name != character.name:
        raise BusinessLogicException("Character name confirmation does not match")

    char_id = character.character_id
    await scenario_service.sessions.delete(char_id)
    await scenario_service.repo.delete_state(char_id)
    await character_sessions.delete_session(char_id)
    await db_session.execute(delete(Character).where(Character.character_id == char_id))
    await db_session.commit()

    payload = await lobby_service.get_start_payload(current_user, db_session)
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.LOBBY),
        payload=payload,
        payload_type="lobby_start",
    )


async def _get_owned_character_or_raise(db_session: AsyncSession, user: User, character_id: int) -> Character:
    stmt = select(Character).where(Character.character_id == character_id, Character.user_id == user.id)
    character = await db_session.scalar(stmt)
    if character is None:
        raise BusinessLogicException("Character is unavailable")
    return character
