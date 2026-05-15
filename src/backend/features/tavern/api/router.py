from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from src.backend.core.auth import User, get_current_user, require_game_character_scope
from src.backend.features.tavern.dependencies import TavernGatewayDep
from src.shared.schemas import CoreResponseDTO, StateTransitionDTO
from src.shared.schemas.tavern import TavernActionDTO, TavernUIPayloadDTO

router = APIRouter(prefix="/tavern", tags=["Tavern"])


@router.get("/v1/{char_id}/view", response_model=CoreResponseDTO[TavernUIPayloadDTO])
async def tavern_view_v1(
    request: Request,
    char_id: int,
    gateway: TavernGatewayDep,
    current_user: Annotated[User, Depends(get_current_user)],
    screen: Annotated[str | None, Query()] = None,
    tavern_id: Annotated[str | None, Query()] = None,
    service_id: Annotated[str | None, Query()] = None,
    location_id: Annotated[str | None, Query()] = None,
) -> CoreResponseDTO[TavernUIPayloadDTO]:
    require_game_character_scope(request, current_user, char_id)
    return await gateway.get_tavern_view(
        current_user,
        char_id,
        screen=screen,
        tavern_id=tavern_id,
        service_id=service_id,
        location_id=location_id,
    )


@router.post("/v1/{char_id}/action", response_model=CoreResponseDTO[TavernUIPayloadDTO | StateTransitionDTO])
async def tavern_action_v1(
    request: Request,
    char_id: int,
    body: TavernActionDTO,
    gateway: TavernGatewayDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CoreResponseDTO[TavernUIPayloadDTO | StateTransitionDTO]:
    require_game_character_scope(request, current_user, char_id)
    return await gateway.handle_tavern_action(current_user, char_id, body)
