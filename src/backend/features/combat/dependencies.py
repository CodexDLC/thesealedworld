from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from src.backend.core.arq import ArqService
from src.backend.features.combat.integrations import CombatSessionIntegration, CombatSystemIntegrator
from src.backend.features.combat.orchestrators import CombatRuntimeOrchestrator
from src.backend.features.combat.services.session_service import CombatSessionService


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
        ),
        arq=arq,
    )


CombatSessionServiceDep = Annotated[CombatSessionService, Depends(get_combat_session_service)]


def get_combat_runtime_orchestrator(service: CombatSessionServiceDep) -> CombatRuntimeOrchestrator:
    return CombatRuntimeOrchestrator(service)


CombatRuntimeOrchestratorDep = Annotated[CombatRuntimeOrchestrator, Depends(get_combat_runtime_orchestrator)]
