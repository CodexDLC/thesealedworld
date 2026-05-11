# src/backend/features/exploration/dependencies.py
from typing import Annotated

from fastapi import Depends, Request

from src.backend.features.exploration.gateway import ExplorationGateway
from src.backend.features.exploration.integrations.encounter_integration import EncounterIntegration
from src.backend.features.exploration.integrations.system_integrator import ExplorationSystemIntegrator
from src.backend.features.exploration.runtime.encounter import EncounterEngine
from src.backend.features.exploration.services.encounter_service import ExplorationEncounterService
from src.backend.features.exploration.services.encounter_session_service import ExplorationEncounterSessionService
from src.backend.features.exploration.services.exploration_service import ExplorationService
from src.backend.features.exploration.services.navigation_service import ExplorationNavigationService


def build_exploration_service(request: Request) -> ExplorationService:
    """
    DI factory for ExplorationService.
    """
    # Infrastructure managers from app state
    character_sessions = request.app.state.character_sessions
    world_store = request.app.state.world_locations
    redis = getattr(request.app.state, "redis", None)
    event_bus = getattr(request.app.state, "events", None)

    integrator = ExplorationSystemIntegrator(character_sessions=character_sessions, world_store=world_store)
    encounter_integration = EncounterIntegration(
        character_sessions=character_sessions,
        world_store=world_store,
        events=event_bus,
        redis=redis,
    )

    encounter_engine = EncounterEngine()

    return ExplorationService(
        integrator=integrator,
        encounter_engine=encounter_engine,
        encounter_integration=encounter_integration,
    )


ExplorationServiceDep = Annotated[ExplorationService, Depends(build_exploration_service)]


def build_exploration_gateway(request: Request) -> ExplorationGateway:
    character_sessions = request.app.state.character_sessions
    world_store = request.app.state.world_locations
    redis = getattr(request.app.state, "redis", None)
    event_bus = getattr(request.app.state, "events", None)

    integrator = ExplorationSystemIntegrator(character_sessions=character_sessions, world_store=world_store)
    encounter_integration = EncounterIntegration(
        character_sessions=character_sessions,
        world_store=world_store,
        events=event_bus,
        redis=redis,
    )
    navigation = ExplorationNavigationService(integrator)
    encounter_sessions = ExplorationEncounterSessionService(encounter_integration)
    encounters = ExplorationEncounterService(
        engine=EncounterEngine(),
        integration=encounter_integration,
        session=encounter_sessions,
        navigation=navigation,
    )
    return ExplorationGateway(navigation=navigation, encounters=encounters)


ExplorationGatewayDep = Annotated[ExplorationGateway, Depends(build_exploration_gateway)]
