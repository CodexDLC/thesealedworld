from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_db
from src.backend.features.character.integrations import CharacterStateIntegrator
from src.backend.features.character.managers.session import CharacterSessionManager
from src.backend.features.character.repositories import CharacterRepository, SkillRepository
from src.backend.features.character.services.status_service import CharacterStatusService
from src.backend.features.inventory.repositories.items import InventoryItemRepository


def get_character_sessions(request: Request) -> CharacterSessionManager:
    return request.app.state.character_sessions


def get_character_state_integrator(
    db_session: Annotated[AsyncSession, Depends(get_db)],
    character_sessions: Annotated[CharacterSessionManager, Depends(get_character_sessions)],
) -> CharacterStateIntegrator:
    return CharacterStateIntegrator(
        character_sessions=character_sessions,
        character_repo=CharacterRepository(db_session),
        inventory_repo=InventoryItemRepository(db_session),
        skill_repo=SkillRepository(db_session),
    )


def get_character_status_service(
    state_integrator: Annotated[CharacterStateIntegrator, Depends(get_character_state_integrator)],
) -> CharacterStatusService:
    return CharacterStatusService(state_integrator=state_integrator)
