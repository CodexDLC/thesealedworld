from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_db
from src.backend.features.character.managers.session import CharacterSessionManager
from src.backend.features.character.repositories import CharacterRepository
from src.backend.features.game_lobby.integrations import GameLobbyIntegration
from src.backend.features.game_lobby.services.character_creation_service import CharacterCreationService
from src.backend.features.game_lobby.services.lobby_service import GameLobbyService
from src.backend.features.items.integrations import ItemPersistenceIntegration
from src.backend.features.items.repositories import ItemInstanceRepository
from src.backend.features.scenario.dependencies import build_scenario_service
from src.backend.features.scenario.services import ScenarioService


def get_character_sessions(request: Request) -> CharacterSessionManager:
    return request.app.state.character_sessions


def get_scenario_service(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
) -> ScenarioService:
    return build_scenario_service(request, db_session)


def get_game_lobby_integration(
    db_session: Annotated[AsyncSession, Depends(get_db)],
    character_sessions: Annotated[CharacterSessionManager, Depends(get_character_sessions)],
    scenario_service: Annotated[ScenarioService, Depends(get_scenario_service)],
) -> GameLobbyIntegration:
    return GameLobbyIntegration(
        character_repo=CharacterRepository(db_session),
        item_persistence=ItemPersistenceIntegration(ItemInstanceRepository(db_session)),
        character_sessions=character_sessions,
        scenario_service=scenario_service,
    )


def get_game_lobby_service(
    integration: Annotated[GameLobbyIntegration, Depends(get_game_lobby_integration)],
) -> GameLobbyService:
    return GameLobbyService(integration)


def get_character_creation_service(
    integration: Annotated[GameLobbyIntegration, Depends(get_game_lobby_integration)],
) -> CharacterCreationService:
    return CharacterCreationService(integration)
