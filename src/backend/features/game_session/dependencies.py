from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_db
from src.backend.features.character.integrations import CharacterStateIntegrator
from src.backend.features.character.repositories import (
    CharacterAttributesRepository,
    CharacterProgressionRepository,
    CharacterRepository,
    SkillRepository,
)
from src.backend.features.expedition import CharacterExpeditionRepository, ExpeditionService
from src.backend.features.game_lobby.integrations import GameLobbyIntegration
from src.backend.features.game_session.integrations import GameSessionIntegrator
from src.backend.features.game_session.services import GameSessionService
from src.backend.features.inventory.repositories.items import InventoryItemRepository
from src.backend.features.items.integrations import ItemPersistenceIntegration
from src.backend.features.items.repositories import ItemInstanceRepository
from src.backend.features.npc.integrations import NpcIntegration
from src.backend.features.rift.integrations import RiftRuntimeIntegration
from src.backend.infrastructure.loot.managers.loot_manager import LootManager
from src.backend.infrastructure.rift.managers import RiftInstanceStore, RiftPresenceStore, RiftRunSessionStore
from src.backend.realtime.integrations.notice_publisher import PlayerNoticePublisher


def get_game_session_service(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
) -> GameSessionService:
    redis = getattr(request.app.state, "redis", None)
    character_sessions = request.app.state.character_sessions
    character_repo = CharacterRepository(db_session)
    attributes_repo = CharacterAttributesRepository(db_session)
    skill_repo = SkillRepository(db_session)
    progression_repo = CharacterProgressionRepository(db_session)
    expedition_repo = CharacterExpeditionRepository(db_session)
    inventory_repo = InventoryItemRepository(db_session)
    integrator = GameSessionIntegrator(
        character_repo=character_repo,
        character_sessions=character_sessions,
        db_session=db_session,
        state_integrator=CharacterStateIntegrator(
            character_sessions=character_sessions,
            character_repo=character_repo,
            skill_repo=skill_repo,
            progression_repo=progression_repo,
            expedition_repo=expedition_repo,
            inventory_repo=inventory_repo,
        ),
        expedition_service=ExpeditionService(
            session=db_session,
            character_sessions=character_sessions,
            expedition_manager=request.app.state.redis_managers.expeditions,
            loot_manager=LootManager(redis),
            world_store=request.app.state.world_locations,
            commit_on_write=True,
            game_config=getattr(request.app.state, "game_config", None),
            notice_publisher=(
                PlayerNoticePublisher(request.app.state.events)
                if getattr(request.app.state, "events", None) is not None
                else None
            ),
        ),
        loot_manager=LootManager(redis),
        loot_arq=getattr(request.app.state, "system_arq", None),
        rift_runtime=RiftRuntimeIntegration(
            instance_store=RiftInstanceStore(redis),
            session_store=RiftRunSessionStore(redis),
            presence_store=RiftPresenceStore(redis),
        ),
        starter_reset_integration=GameLobbyIntegration(
            character_repo=character_repo,
            attributes_repo=attributes_repo,
            skill_repo=skill_repo,
            progression_repo=progression_repo,
            expedition_repo=expedition_repo,
            inventory_repo=inventory_repo,
            item_persistence=ItemPersistenceIntegration(ItemInstanceRepository(db_session)),
            inventory_sessions=request.app.state.redis_managers.inventory_sessions,
            character_sessions=character_sessions,
            events=request.app.state.events,
        ),
    )
    npc = NpcIntegration.from_session(db_session)
    return GameSessionService(integrator=integrator).bind_npc(npc)
