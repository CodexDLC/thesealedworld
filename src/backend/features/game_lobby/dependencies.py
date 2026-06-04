from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_db
from src.backend.core.mongo import get_mongo_provider
from src.backend.features.character.repositories import (
    CharacterAttributesRepository,
    CharacterProgressionRepository,
    CharacterRepository,
    SkillRepository,
    SymbioteRepository,
)
from src.backend.features.expedition import CharacterExpeditionRepository
from src.backend.features.game_lobby.integrations import GameLobbyIntegration
from src.backend.features.game_lobby.services.character_creation_service import CharacterCreationService
from src.backend.features.game_lobby.services.lobby_service import GameLobbyService
from src.backend.features.inventory.repositories.items import InventoryItemRepository
from src.backend.features.items.integrations import ItemPersistenceIntegration
from src.backend.features.items.repositories import ItemInstanceRepository
from src.backend.features.rift.integrations import RiftRuntimeIntegration
from src.backend.infrastructure.actor_state.managers import CharacterSessionManager, GameSessionLockManager
from src.backend.infrastructure.rift.managers import (
    RiftInstanceStore,
    RiftPortalStore,
    RiftPresenceStore,
    RiftRestoreLock,
    RiftRunSessionStore,
)
from src.backend.infrastructure.rift.repositories import RiftMembershipRepository
from src.backend.infrastructure.rift.repositories.snapshots import RiftRuntimeSnapshotRepository


def get_character_sessions(request: Request) -> CharacterSessionManager:
    return request.app.state.character_sessions


def get_game_session_lock(request: Request) -> GameSessionLockManager:
    return request.app.state.game_session_lock


def get_game_lobby_integration(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    character_sessions: Annotated[CharacterSessionManager, Depends(get_character_sessions)],
    game_session_lock: Annotated[GameSessionLockManager, Depends(get_game_session_lock)],
) -> GameLobbyIntegration:
    return GameLobbyIntegration(
        character_repo=CharacterRepository(db_session),
        attributes_repo=CharacterAttributesRepository(db_session),
        skill_repo=SkillRepository(db_session),
        progression_repo=CharacterProgressionRepository(db_session),
        symbiote_repo=SymbioteRepository(db_session),
        expedition_repo=CharacterExpeditionRepository(db_session),
        inventory_repo=InventoryItemRepository(db_session),
        item_persistence=ItemPersistenceIntegration(ItemInstanceRepository(db_session)),
        inventory_sessions=request.app.state.redis_managers.inventory_sessions,
        character_sessions=character_sessions,
        game_session_lock=game_session_lock,
        events=request.app.state.events,
        starting_imprint_distribution=request.app.state.redis_managers.starting_imprints,
        rift_runtime=RiftRuntimeIntegration(
            instance_store=RiftInstanceStore(request.app.state.redis),
            session_store=RiftRunSessionStore(request.app.state.redis),
            presence_store=RiftPresenceStore(request.app.state.redis),
            portal_store=RiftPortalStore(request.app.state.redis),
            membership_repository=RiftMembershipRepository(db_session),
            snapshot_repository=RiftRuntimeSnapshotRepository(get_mongo_provider().database()),
            restore_lock=RiftRestoreLock(request.app.state.redis),
        ),
    )


def get_game_lobby_service(
    integration: Annotated[GameLobbyIntegration, Depends(get_game_lobby_integration)],
) -> GameLobbyService:
    return GameLobbyService(integration)


def get_character_creation_service(
    integration: Annotated[GameLobbyIntegration, Depends(get_game_lobby_integration)],
) -> CharacterCreationService:
    return CharacterCreationService(integration)
