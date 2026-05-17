from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_db
from src.backend.features.city_services.gateway import CityServiceGateway
from src.backend.features.city_services.integrations import CityServiceSystemIntegrator
from src.backend.features.city_services.repositories import TavernRoomRepository
from src.backend.features.city_services.services import CityService


def get_city_service(request: Request, db_session: Annotated[AsyncSession, Depends(get_db)]) -> CityService:
    integrator = CityServiceSystemIntegrator(
        character_sessions=request.app.state.character_sessions,
        world_store=request.app.state.world_locations,
        room_repository=TavernRoomRepository(db_session),
        events=request.app.state.events,
    )
    return CityService(integrator=integrator)


def get_city_service_gateway(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
) -> CityServiceGateway:
    return CityServiceGateway(service=get_city_service(request, db_session))


CityServiceGatewayDep = Annotated[CityServiceGateway, Depends(get_city_service_gateway)]
