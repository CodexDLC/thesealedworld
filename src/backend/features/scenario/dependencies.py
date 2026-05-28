from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.bus import GameEventProducer
from src.backend.features.character.repositories import CharacterRepository
from src.backend.features.npc.integrations import NpcIntegration
from src.backend.features.scenario.engine import ScenarioDirector, ScenarioEvaluator, ScenarioFormatter
from src.backend.features.scenario.integrations.content_integration import ScenarioContentIntegration
from src.backend.features.scenario.integrations.system_integrator import ScenarioSystemIntegrator
from src.backend.features.scenario.services.scenario_service import ScenarioService
from src.backend.features.world.integrations import WorldDataIntegration
from src.backend.infrastructure.actor_state.managers import CharacterSessionManager
from src.backend.infrastructure.scenario.managers.session_manager import ScenarioSessionManager
from src.backend.infrastructure.scenario.repositories import ScenarioRepository
from src.backend.infrastructure.world.repositories import WorldRepository


def build_scenario_service(request: Request | Any, db_session: AsyncSession) -> ScenarioService:
    repo = ScenarioRepository(db_session)
    npc = NpcIntegration.from_session(db_session)
    evaluator = ScenarioEvaluator()
    director = ScenarioDirector(evaluator)
    formatter = ScenarioFormatter(director)
    content = ScenarioContentIntegration(repo, request.app.state.scenario_content)
    integrator = ScenarioSystemIntegrator(
        sessions=request.app.state.scenario_sessions,
        content=content,
        character_sessions=request.app.state.character_sessions,
        repo=repo,
        events=request.app.state.events,
        character_repo=CharacterRepository(db_session),
        world_data=WorldDataIntegration(WorldRepository(db_session)),
        npc=npc,
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
