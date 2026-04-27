# src/backend/dependencies/internal/world.py
"""
Dependency Injection для домена World.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.database.redis.manager.world_manager import WorldManager
from backend.dependencies.base import RedisContainerDep
from backend.domains.internal_systems.world.gateway.world_gateway import WorldGateway
from backend.domains.internal_systems.world.services.world_service import WorldService
from backend.domains.internal_systems.world.services.world_session_service import WorldSessionService


def get_world_manager(container: RedisContainerDep) -> WorldManager:
    """
    Получает WorldManager из контейнера.
    """
    return container.world_manager


WorldManagerDep = Annotated[WorldManager, Depends(get_world_manager)]


async def get_world_session_service(world_mgr: WorldManagerDep) -> WorldSessionService:
    """
    Создает WorldSessionService.
    """
    return WorldSessionService(world_manager=world_mgr)


WorldSessionServiceDep = Annotated[WorldSessionService, Depends(get_world_session_service)]


async def get_world_service(
    session_service: WorldSessionServiceDep,
    db_session: AsyncSession = Depends(get_db),
) -> WorldService:
    """
    Создает WorldService.
    """
    return WorldService(session_service=session_service, db_session=db_session)


WorldServiceDep = Annotated[WorldService, Depends(get_world_service)]


async def get_world_gateway(service: WorldServiceDep) -> WorldGateway:
    """
    Создает WorldGateway.
    """
    return WorldGateway(service=service)


WorldGatewayDep = Annotated[WorldGateway, Depends(get_world_gateway)]
