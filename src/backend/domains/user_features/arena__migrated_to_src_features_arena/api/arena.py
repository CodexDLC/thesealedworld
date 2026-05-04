from fastapi import APIRouter, Depends

from src.backend.dependencies.features.arena import get_arena_gateway
from src.backend.domains.user_features.arena.gateway.arena_gateway import ArenaGateway
from src.shared.schemas.arena import ArenaActionDTO
from src.shared.schemas.response import CoreResponseDTO

router = APIRouter(prefix="/arena", tags=["Arena"])


@router.post("/{char_id}/action", response_model=CoreResponseDTO)
async def arena_action(char_id: int, body: ArenaActionDTO, gateway: ArenaGateway = Depends(get_arena_gateway)):
    """
    Единая точка входа для действий на Арене.
    """
    return await gateway.handle_action(char_id, body.action, body.mode, body.value)
