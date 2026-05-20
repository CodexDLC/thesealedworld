from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from src.backend.core.database import get_db
from src.backend.features.character.repositories import CharacterRepository
from src.backend.features.inventory.integrations import InventoryStreamClient
from src.backend.features.inventory.repositories.items import InventoryItemRepository
from src.backend.features.inventory.services.inventory_service import InventoryService
from src.backend.features.inventory.services.session_manager import InventorySessionManager

if TYPE_CHECKING:
    from src.backend.features.character.managers.session import CharacterSessionManager


def get_inventory_service(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
) -> InventoryService:
    character_sessions: CharacterSessionManager = request.app.state.character_sessions
    return InventoryService(
        repository=InventoryItemRepository(db_session),
        inventory_sessions=InventorySessionManager(request.app.state.redis),
        character_sessions=character_sessions,
        stream_client=InventoryStreamClient(request.app.state.events),
    )


def get_character_repository(db_session: Annotated[AsyncSession, Depends(get_db)]) -> CharacterRepository:
    return CharacterRepository(db_session)
