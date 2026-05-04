# src/backend/features/exploration/dependencies.py
from typing import Annotated

from fastapi import Depends, Request

from src.backend.features.exploration.events.emitters import ExplorationEvents
from src.backend.features.exploration.integrations.system_integrator import ExplorationSystemIntegrator
from src.backend.features.exploration.runtime.encounter import EncounterEngine
from src.backend.features.exploration.services.exploration_service import ExplorationService


def build_exploration_service(request: Request) -> ExplorationService:
    """
    DI factory for ExplorationService.
    """
    # Infrastructure managers from app state
    character_sessions = request.app.state.character_sessions
    world_store = request.app.state.world_locations

    events = ExplorationEvents()

    integrator = ExplorationSystemIntegrator(character_sessions=character_sessions, world_store=world_store)

    encounter_engine = EncounterEngine(events=events)

    return ExplorationService(integrator=integrator, encounter_engine=encounter_engine)


ExplorationServiceDep = Annotated[ExplorationService, Depends(build_exploration_service)]
