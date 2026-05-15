from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_db
from src.backend.features.tavern.gateway import TavernGateway
from src.backend.features.tavern.integrations import TavernSystemIntegrator
from src.backend.features.tavern.repositories import TavernRoomRepository
from src.backend.features.tavern.services import TavernService


def get_tavern_service(request: Request, db_session: Annotated[AsyncSession, Depends(get_db)]) -> TavernService:
    integrator = TavernSystemIntegrator(
        character_sessions=request.app.state.character_sessions,
        world_store=request.app.state.world_locations,
        room_repository=TavernRoomRepository(db_session),
        events=request.app.state.events,
    )
    return TavernService(integrator=integrator)


def get_tavern_gateway(request: Request, db_session: Annotated[AsyncSession, Depends(get_db)]) -> TavernGateway:
    return TavernGateway(tavern=get_tavern_service(request, db_session))


TavernGatewayDep = Annotated[TavernGateway, Depends(get_tavern_gateway)]
