from typing import Annotated

from fastapi import Depends

# Infrastructure
from src.backend.core.base_arq import ArqService
from src.backend.dependencies.base import RedisContainerDep
from src.backend.dependencies.internal.context import ContextAssemblerServiceDep
from src.backend.domains.user_features.combat.orchestrators.combat_entry_orchestrator import CombatEntryOrchestrator
from src.backend.domains.user_features.combat.orchestrators.combat_gateway import CombatGateway

# Services (Runtime)
from src.backend.domains.user_features.combat.orchestrators.handler.combat_session_service import CombatSessionService

# Services (Initialization)
from src.backend.domains.user_features.combat.orchestrators.handler.initialization.combat_lifecycle_service import (
    CombatLifecycleService,
)
from src.backend.domains.user_features.combat.orchestrators.handler.runtime.combat_turn_manager import CombatTurnManager
from src.backend.domains.user_features.combat.orchestrators.handler.runtime.combat_view_service import CombatViewService

# --- 1. Runtime Services ---


async def get_combat_session_service(
    redis_container: RedisContainerDep,
) -> CombatSessionService:
    """
    Factory for CombatSessionService.
    """
    arq_service = ArqService()

    turn_manager = CombatTurnManager(combat_manager=redis_container.combat, arq_service=arq_service)

    view_service = CombatViewService()

    return CombatSessionService(
        account_manager=redis_container.account,
        combat_manager=redis_container.combat,
        turn_manager=turn_manager,
        view_service=view_service,
    )


CombatSessionServiceDep = Annotated[CombatSessionService, Depends(get_combat_session_service)]


async def get_combat_gateway(session_service: CombatSessionServiceDep) -> CombatGateway:
    """
    Factory for CombatGateway.
    """
    return CombatGateway(session_service=session_service)


CombatGatewayDep = Annotated[CombatGateway, Depends(get_combat_gateway)]

# --- 2. Initialization Services ---


async def get_combat_lifecycle_service(redis_container: RedisContainerDep) -> CombatLifecycleService:
    """
    Factory for CombatLifecycleService.
    """
    arq_service = ArqService()

    return CombatLifecycleService(
        combat_manager=redis_container.combat,
        account_manager=redis_container.account,
        context_manager=redis_container.context,
        arq_service=arq_service,
    )


CombatLifecycleServiceDep = Annotated[CombatLifecycleService, Depends(get_combat_lifecycle_service)]

# --- 3. Entry service ---


async def get_combat_entry_orchestrator(
    lifecycle: CombatLifecycleServiceDep, session: CombatSessionServiceDep, assembler: ContextAssemblerServiceDep
) -> CombatEntryOrchestrator:
    """
    Factory for CombatEntryOrchestrator.
    Now it's a full dependency, not just a helper function.
    """
    return CombatEntryOrchestrator(lifecycle_service=lifecycle, session_service=session, assembler=assembler)


CombatEntryOrchestratorDep = Annotated[CombatEntryOrchestrator, Depends(get_combat_entry_orchestrator)]
