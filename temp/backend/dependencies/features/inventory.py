from typing import Annotated

from fastapi import Depends

from src.backend.database.redis.manager.inventory_manager import InventoryManager
from src.backend.dependencies.base import RedisContainerDep
from src.backend.dependencies.internal.context import ContextAssemblerServiceDep
from src.backend.dependencies.internal.dispatcher import SystemDispatcherDep
from src.backend.domains.user_features.inventory.engine.dispatcher_bridge import InventoryDispatcherBridge
from src.backend.domains.user_features.inventory.engine.inventory_enricher import InventoryEnricher
from src.backend.domains.user_features.inventory.gateway.inventory_gateway import InventoryGateway
from src.backend.domains.user_features.inventory.services.inventory_service import InventoryService
from src.backend.domains.user_features.inventory.services.inventory_session_service import InventorySessionService


# --- 1. Managers ---
async def get_inventory_manager(container: RedisContainerDep) -> InventoryManager:
    """Возвращает менеджер инвентаря."""
    return container.inventory


InventoryManagerDep = Annotated[InventoryManager, Depends(get_inventory_manager)]


# --- 2. Engines (Bridge, Enricher) ---
async def get_inventory_bridge(dispatcher: SystemDispatcherDep) -> InventoryDispatcherBridge:
    """Возвращает мост диспетчера инвентаря."""
    return InventoryDispatcherBridge(dispatcher)


InventoryDispatcherBridgeDep = Annotated[InventoryDispatcherBridge, Depends(get_inventory_bridge)]


async def get_inventory_enricher() -> InventoryEnricher:
    """Возвращает обогатитель инвентаря."""
    return InventoryEnricher()


InventoryEnricherDep = Annotated[InventoryEnricher, Depends(get_inventory_enricher)]


# --- 3. Domain Services ---
async def get_inventory_session_service(
    manager: InventoryManagerDep, assembler: ContextAssemblerServiceDep
) -> InventorySessionService:
    """Возвращает сервис сессий инвентаря."""
    return InventorySessionService(manager, assembler)


InventorySessionServiceDep = Annotated[InventorySessionService, Depends(get_inventory_session_service)]


async def get_inventory_service(
    session_service: InventorySessionServiceDep, enricher: InventoryEnricherDep, bridge: InventoryDispatcherBridgeDep
) -> InventoryService:
    """Возвращает сервис инвентаря."""
    return InventoryService(session_service, enricher, bridge)


InventoryServiceDep = Annotated[InventoryService, Depends(get_inventory_service)]


# --- 4. Gateway ---
async def get_inventory_gateway(service: InventoryServiceDep) -> InventoryGateway:
    """Возвращает шлюз инвентаря."""
    return InventoryGateway(service)


InventoryGatewayDep = Annotated[InventoryGateway, Depends(get_inventory_gateway)]
