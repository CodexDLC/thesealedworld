from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_db
from src.backend.features.character.repositories import CharacterRepository
from src.backend.features.game_session.integrations import GameSessionIntegrator
from src.backend.features.game_session.services import GameSessionService
from src.backend.features.scenario.dependencies import build_scenario_service
from src.backend.features.scenario.services import ScenarioService


def get_scenario_service(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
) -> ScenarioService:
    return build_scenario_service(request, db_session)


def get_game_session_service(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    scenario_service: Annotated[ScenarioService, Depends(get_scenario_service)],
) -> GameSessionService:
    integrator = GameSessionIntegrator(
        character_repo=CharacterRepository(db_session),
        character_sessions=request.app.state.character_sessions,
        scenario_service=scenario_service,
    )
    return GameSessionService(integrator=integrator)
