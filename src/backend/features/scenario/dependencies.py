from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.bus import GameEventProducer
from src.backend.features.scenario.engine import ScenarioDirector, ScenarioEvaluator, ScenarioFormatter
from src.backend.features.scenario.integrations.system_integrator import ScenarioSystemIntegrator
from src.backend.features.scenario.services.scenario_service import ScenarioService
from src.backend.infrastructure.actor_state import CharacterSessionManager
from src.backend.infrastructure.scenario.managers.content_manager import ScenarioContentManager
from src.backend.infrastructure.scenario.managers.session_manager import ScenarioSessionManager
from src.backend.infrastructure.scenario.repositories import ScenarioRepository


def build_scenario_service(request: Request | Any, db_session: AsyncSession) -> ScenarioService:
    repo = ScenarioRepository(db_session)
    evaluator = ScenarioEvaluator()
    director = ScenarioDirector(evaluator)
    formatter = ScenarioFormatter(director)
    content_manager = ScenarioContentManager(request.app.state.redis)
    integrator = ScenarioSystemIntegrator(
        sessions=request.app.state.scenario_sessions,
        content_manager=content_manager,
        character_sessions=request.app.state.character_sessions,
        repo=repo,
        events=request.app.state.events,
        redis=request.app.state.redis,
    )
    return ScenarioService(
        integrator=integrator,
        evaluator=evaluator,
        director=director,
        formatter=formatter,
    )


def get_events(request: Request) -> GameEventProducer:
    return request.app.state.events


def get_character_sessions(request: Request) -> CharacterSessionManager:
    return request.app.state.character_sessions


def get_scenario_sessions(request: Request) -> ScenarioSessionManager:
    return request.app.state.scenario_sessions
