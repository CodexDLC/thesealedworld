from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.bus import GameEventProducer
from src.backend.features.scenario.engine import ScenarioDirector, ScenarioEvaluator, ScenarioFormatter
from src.backend.features.scenario.services.content_service import ScenarioContentService
from src.backend.features.scenario.services.scenario_service import ScenarioService
from src.backend.infrastructure.db.scenario.repositories import ScenarioRepository
from src.backend.infrastructure.redis.character_session_manager import CharacterSessionManager
from src.backend.infrastructure.redis.scenario import ScenarioSessionManager


def build_scenario_service(request: Request | Any, db_session: AsyncSession) -> ScenarioService:
    repo = ScenarioRepository(db_session)
    evaluator = ScenarioEvaluator()
    director = ScenarioDirector(evaluator)
    formatter = ScenarioFormatter(director)
    return ScenarioService(
        content=ScenarioContentService(repo, request.app.state.redis),
        sessions=request.app.state.scenario_sessions,
        character_sessions=request.app.state.character_sessions,
        repo=repo,
        evaluator=evaluator,
        director=director,
        formatter=formatter,
        events=request.app.state.events,
        redis=request.app.state.redis,
    )


def get_events(request: Request) -> GameEventProducer:
    return request.app.state.events


def get_character_sessions(request: Request) -> CharacterSessionManager:
    return request.app.state.character_sessions


def get_scenario_sessions(request: Request) -> ScenarioSessionManager:
    return request.app.state.scenario_sessions
