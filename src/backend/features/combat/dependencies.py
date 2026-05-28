from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from src.backend.core.arq import ArqService
from src.backend.core.database import get_db
from src.backend.features.combat.integrations import CombatSessionIntegration, CombatSystemIntegrator
from src.backend.features.combat.integrations.analytics_dashboard import CombatAnalyticsDashboardIntegration
from src.backend.features.combat.orchestrators import CombatRuntimeOrchestrator
from src.backend.features.combat.services.analytics_dashboard_service import CombatAnalyticsDashboardService
from src.backend.features.combat.services.session_service import CombatSessionService
from src.backend.features.rift.integrations import RiftRuntimeIntegration
from src.backend.infrastructure.combat.repositories import CombatAnalyticsRepository
from src.backend.infrastructure.rift.managers import RiftInstanceStore, RiftPresenceStore, RiftRunSessionStore


def get_combat_session_service(request: Request) -> CombatSessionService:
    app_state = request.app.state
    arq = getattr(app_state, "arq", None) or getattr(app_state, "combat_arq", None) or ArqService()
    return CombatSessionService(
        store=CombatSessionIntegration.from_redis(app_state.redis),
        system_integrator=CombatSystemIntegrator(
            actor_commitments=app_state.actor_commitments,
            character_sessions=app_state.character_sessions,
            events=app_state.events,
            redis=app_state.redis,
            rift_runtime=RiftRuntimeIntegration(
                instance_store=RiftInstanceStore(app_state.redis),
                session_store=RiftRunSessionStore(app_state.redis),
                presence_store=RiftPresenceStore(app_state.redis),
            ),
        ),
        arq=arq,
    )


CombatSessionServiceDep = Annotated[CombatSessionService, Depends(get_combat_session_service)]


def get_combat_runtime_orchestrator(service: CombatSessionServiceDep) -> CombatRuntimeOrchestrator:
    return CombatRuntimeOrchestrator(service)


CombatRuntimeOrchestratorDep = Annotated[CombatRuntimeOrchestrator, Depends(get_combat_runtime_orchestrator)]


def get_combat_analytics_dashboard_service(
    db_session: Annotated[AsyncSession, Depends(get_db)],
) -> CombatAnalyticsDashboardService:
    return CombatAnalyticsDashboardService(
        CombatAnalyticsDashboardIntegration(CombatAnalyticsRepository(db_session)),
    )


CombatAnalyticsDashboardServiceDep = Annotated[
    CombatAnalyticsDashboardService,
    Depends(get_combat_analytics_dashboard_service),
]
