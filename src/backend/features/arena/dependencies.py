from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_db
from src.backend.features.arena.dto.session import ArenaCombatRequestDTO, ArenaQueueRequestDTO, ArenaRuntimeSessionDTO
from src.backend.features.arena.gateway import ArenaGateway
from src.backend.features.arena.integrations import ArenaSessionIntegration, ArenaSystemIntegrator
from src.backend.features.arena.services import (
    ArenaDuelService,
    ArenaGroupService,
    ArenaRatingViewService,
    ArenaService,
    RatingService,
    SeasonService,
)
from src.backend.infrastructure.arena.managers import ArenaSessionManager
from src.backend.infrastructure.arena.repositories import (
    ArenaLeagueRepository,
    ArenaMatchRepository,
    ArenaRatingRepository,
    ArenaSeasonRepository,
)


def get_arena_service(request: Request, db_session: Annotated[AsyncSession, Depends(get_db)]) -> ArenaService:
    store = ArenaSessionManager(
        request.app.state.redis,
        queue_schema=ArenaQueueRequestDTO,
        combat_schema=ArenaCombatRequestDTO,
        runtime_schema=ArenaRuntimeSessionDTO,
    )
    session_service = ArenaSessionIntegration(store)
    integrator = ArenaSystemIntegrator(
        events=request.app.state.events,
        character_sessions=request.app.state.character_sessions,
    )
    rating_view = ArenaRatingViewService(
        seasons=SeasonService(seasons=ArenaSeasonRepository(db_session)),
        ratings=RatingService(
            ratings=ArenaRatingRepository(db_session),
            matches=ArenaMatchRepository(db_session),
            leagues=ArenaLeagueRepository(db_session),
        ),
        db_session=db_session,
    )
    return ArenaService(session_service=session_service, integrator=integrator, rating_view=rating_view)


def get_arena_gateway(request: Request, db_session: Annotated[AsyncSession, Depends(get_db)]) -> ArenaGateway:
    arena = get_arena_service(request, db_session)
    duel = ArenaDuelService(arena=arena)
    group = ArenaGroupService(arena=arena)
    return ArenaGateway(arena=arena, duel=duel, group=group)


ArenaServiceDep = Annotated[ArenaService, Depends(get_arena_service)]
ArenaGatewayDep = Annotated[ArenaGateway, Depends(get_arena_gateway)]
