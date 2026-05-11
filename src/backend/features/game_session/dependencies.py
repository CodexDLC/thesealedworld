from fastapi import Request

from src.backend.features.game_session.integrations import GameSessionIntegrator
from src.backend.features.game_session.services import GameSessionService


def get_game_session_service(
    request: Request,
) -> GameSessionService:
    integrator = GameSessionIntegrator(
        character_sessions=request.app.state.character_sessions,
    )
    return GameSessionService(integrator=integrator)
