from typing import Any

from fastapi import APIRouter, Depends, Query

from src.backend.dependencies.features.game_menu import get_menu_gateway
from src.backend.domains.user_features.game_menu.gateway.menu_gateway import GameMenuGateway
from src.shared.schemas.game_menu import GameMenuDTO, MenuActionRequest
from src.shared.schemas.response import CoreResponseDTO

router = APIRouter(prefix="/api/v1/game-menu", tags=["Game Menu"])


@router.get("/view", response_model=CoreResponseDTO[GameMenuDTO])
async def get_menu_view(
    char_id: int = Query(..., description="Character ID"), gateway: GameMenuGateway = Depends(get_menu_gateway)
):
    """
    Получить текущее состояние меню (HUD + кнопки).
    """
    return await gateway.get_view(char_id)


@router.post("/dispatch", response_model=CoreResponseDTO[Any])
async def dispatch_action(request: MenuActionRequest, gateway: GameMenuGateway = Depends(get_menu_gateway)):
    """
    Выполнить действие меню (переход).
    """
    return await gateway.dispatch_action(request.char_id, request.action_id)
