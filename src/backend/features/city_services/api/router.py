from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from src.backend.core.auth import User, get_current_user, require_game_character_scope
from src.backend.features.city_services.dependencies import CityServiceGatewayDep
from src.shared.schemas import CoreResponseDTO, StateTransitionDTO
from src.shared.schemas.city_services import CityServiceActionDTO, CityServiceUIPayloadDTO

router = APIRouter(prefix="/city-services", tags=["City Services"])


@router.get("/v1/{char_id}/view", response_model=CoreResponseDTO[CityServiceUIPayloadDTO])
async def city_service_view_v1(
    request: Request,
    char_id: int,
    gateway: CityServiceGatewayDep,
    current_user: Annotated[User, Depends(get_current_user)],
    service_id: Annotated[str | None, Query()] = None,
    screen: Annotated[str | None, Query()] = None,
    section_id: Annotated[str | None, Query()] = None,
    location_id: Annotated[str | None, Query()] = None,
    tavern_id: Annotated[str | None, Query()] = None,
) -> CoreResponseDTO[CityServiceUIPayloadDTO]:
    require_game_character_scope(request, current_user, char_id)
    return await gateway.get_view(
        current_user,
        char_id,
        service_id=service_id,
        screen=screen,
        section_id=section_id,
        location_id=location_id,
        tavern_id=tavern_id,
    )


@router.post("/v1/{char_id}/action", response_model=CoreResponseDTO[CityServiceUIPayloadDTO | StateTransitionDTO])
async def city_service_action_v1(
    request: Request,
    char_id: int,
    body: CityServiceActionDTO,
    gateway: CityServiceGatewayDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CoreResponseDTO[CityServiceUIPayloadDTO | StateTransitionDTO]:
    require_game_character_scope(request, current_user, char_id)
    return await gateway.handle_action(current_user, char_id, body)
