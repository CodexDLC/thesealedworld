from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_db
from src.backend.features.character.managers.session import CharacterSessionManager
from src.backend.features.character.repositories import (
    CharacterAttributesRepository,
    CharacterProgressionRepository,
    CharacterRepository,
    SkillRepository,
)
from src.backend.features.expedition import CharacterExpeditionRepository
from src.backend.features.game_lobby.integrations import GameLobbyIntegration
from src.backend.features.game_lobby.services.character_creation_service import CharacterCreationService
from src.backend.features.game_lobby.services.lobby_service import GameLobbyService
from src.backend.features.inventory.repositories.items import InventoryItemRepository
from src.backend.features.items.integrations import ItemPersistenceIntegration
from src.backend.features.items.repositories import ItemInstanceRepository


def get_character_sessions(request: Request) -> CharacterSessionManager:
    return request.app.state.character_sessions


def get_game_lobby_integration(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    character_sessions: Annotated[CharacterSessionManager, Depends(get_character_sessions)],
) -> GameLobbyIntegration:
    return GameLobbyIntegration(
        character_repo=CharacterRepository(db_session),
        attributes_repo=CharacterAttributesRepository(db_session),
        skill_repo=SkillRepository(db_session),
        progression_repo=CharacterProgressionRepository(db_session),
        expedition_repo=CharacterExpeditionRepository(db_session),
        inventory_repo=InventoryItemRepository(db_session),
        item_persistence=ItemPersistenceIntegration(ItemInstanceRepository(db_session)),
        character_sessions=character_sessions,
        events=request.app.state.events,
    )


def get_game_lobby_service(
    integration: Annotated[GameLobbyIntegration, Depends(get_game_lobby_integration)],
) -> GameLobbyService:
    return GameLobbyService(integration)


def get_character_creation_service(
    integration: Annotated[GameLobbyIntegration, Depends(get_game_lobby_integration)],
) -> CharacterCreationService:
    return CharacterCreationService(integration)
