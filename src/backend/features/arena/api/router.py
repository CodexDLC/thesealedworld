from typing import Annotated

from fastapi import APIRouter, Depends, Request

from src.backend.core.auth import User, get_current_user, require_game_character_scope
from src.backend.features.arena.dependencies import ArenaGatewayDep
from src.shared.schemas.arena import ArenaActionDTO, ArenaUIPayloadDTO
from src.shared.schemas.response import CoreResponseDTO, StateTransitionDTO

router = APIRouter(prefix="/arena", tags=["Arena"])


@router.get("/v2/{char_id}/view", response_model=CoreResponseDTO[ArenaUIPayloadDTO])
async def arena_view_v2(
    request: Request,
    char_id: int,
    gateway: ArenaGatewayDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CoreResponseDTO[ArenaUIPayloadDTO]:
    require_game_character_scope(request, current_user, char_id)
    return await gateway.get_arena_view(current_user, char_id)


@router.post("/v2/{char_id}/action", response_model=CoreResponseDTO[ArenaUIPayloadDTO | StateTransitionDTO])
async def arena_action_v2(
    request: Request,
    char_id: int,
    body: ArenaActionDTO,
    gateway: ArenaGatewayDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CoreResponseDTO[ArenaUIPayloadDTO | StateTransitionDTO]:
    require_game_character_scope(request, current_user, char_id)
    return await gateway.handle_arena_action(current_user, char_id, body)


@router.get("/v2/{char_id}/duel/view", response_model=CoreResponseDTO[ArenaUIPayloadDTO])
async def arena_duel_view_v2(
    request: Request,
    char_id: int,
    gateway: ArenaGatewayDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CoreResponseDTO[ArenaUIPayloadDTO]:
    require_game_character_scope(request, current_user, char_id)
    return await gateway.get_duel_view(current_user, char_id)


@router.post("/v2/{char_id}/duel/action", response_model=CoreResponseDTO[ArenaUIPayloadDTO | StateTransitionDTO])
async def arena_duel_action_v2(
    request: Request,
    char_id: int,
    body: ArenaActionDTO,
    gateway: ArenaGatewayDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CoreResponseDTO[ArenaUIPayloadDTO | StateTransitionDTO]:
    require_game_character_scope(request, current_user, char_id)
    return await gateway.handle_duel_action(current_user, char_id, body)


@router.get("/v2/{char_id}/group/lobby", response_model=CoreResponseDTO[ArenaUIPayloadDTO])
async def arena_group_lobby_v2(
    request: Request,
    char_id: int,
    gateway: ArenaGatewayDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CoreResponseDTO[ArenaUIPayloadDTO]:
    require_game_character_scope(request, current_user, char_id)
    return await gateway.get_group_view(current_user, char_id)


@router.post("/v2/{char_id}/group/action", response_model=CoreResponseDTO[ArenaUIPayloadDTO])
async def arena_group_action_v2(
    request: Request,
    char_id: int,
    body: ArenaActionDTO,
    gateway: ArenaGatewayDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CoreResponseDTO[ArenaUIPayloadDTO]:
    require_game_character_scope(request, current_user, char_id)
    return await gateway.handle_group_action(current_user, char_id, body)
