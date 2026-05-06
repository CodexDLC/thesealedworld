from typing import Annotated

from fastapi import Depends, Request

from src.backend.features.arena.integrations import ArenaSessionIntegration, ArenaSystemIntegrator
from src.backend.features.arena.repositories.session_store import ArenaSessionStore
from src.backend.features.arena.services import ArenaService


def get_arena_service(request: Request) -> ArenaService:
    store = ArenaSessionStore(request.app.state.redis)
    session_service = ArenaSessionIntegration(store)
    integrator = ArenaSystemIntegrator(
        events=request.app.state.events,
        character_sessions=request.app.state.character_sessions,
    )
    return ArenaService(session_service=session_service, integrator=integrator)


ArenaServiceDep = Annotated[ArenaService, Depends(get_arena_service)]
