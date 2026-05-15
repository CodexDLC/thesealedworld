from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_db
from src.backend.features.character.integrations import CharacterStateIntegrator
from src.backend.features.character.repositories import (
    CharacterProgressionRepository,
    CharacterRepository,
    SkillRepository,
)
from src.backend.features.expedition import CharacterExpeditionRepository, ExpeditionService
from src.backend.features.game_session.integrations import GameSessionIntegrator
from src.backend.features.game_session.services import GameSessionService
from src.backend.features.inventory.repositories.items import InventoryItemRepository
from src.backend.infrastructure.loot.managers.loot_manager import LootManager


def get_game_session_service(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
) -> GameSessionService:
    redis = getattr(request.app.state, "redis", None)
    character_sessions = request.app.state.character_sessions
    integrator = GameSessionIntegrator(
        character_sessions=character_sessions,
        db_session=db_session,
        state_integrator=CharacterStateIntegrator(
            character_sessions=character_sessions,
            character_repo=CharacterRepository(db_session),
            skill_repo=SkillRepository(db_session),
            progression_repo=CharacterProgressionRepository(db_session),
            expedition_repo=CharacterExpeditionRepository(db_session),
            inventory_repo=InventoryItemRepository(db_session),
        ),
        expedition_service=ExpeditionService(
            session=db_session,
            character_sessions=character_sessions,
            expedition_manager=request.app.state.redis_managers.expeditions,
            loot_manager=LootManager(redis),
            world_store=request.app.state.world_locations,
            commit_on_write=True,
        ),
    )
    return GameSessionService(integrator=integrator)
