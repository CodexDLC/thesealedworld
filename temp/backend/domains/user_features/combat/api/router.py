from typing import Any

from fastapi import APIRouter, Body, Query

from src.backend.dependencies.features.combat import CombatGatewayDep
from src.shared.schemas.response import CoreResponseDTO

router = APIRouter()


@router.post("/{char_id}/action", response_model=CoreResponseDTO)
async def handle_combat_action(
    char_id: int,
    gateway: CombatGatewayDep,
    action_type: str = Body(..., embed=True),  # Ожидаем {"action_type": "attack", ...} или просто в теле
    payload: dict[str, Any] = Body(...),
) -> CoreResponseDTO:
    """
    Обработка боевого действия (Атака, Скилл, Предмет).
    """
    # Если action_type не передан в payload, берем из аргумента
    if "action" not in payload:
        payload["action"] = action_type

    return await gateway.handle_action(char_id, action_type, payload)


@router.get("/{char_id}/view", response_model=CoreResponseDTO)
async def get_combat_view(
    char_id: int,
    gateway: CombatGatewayDep,
    view_type: str = Query(..., description="snapshot, logs, history"),
    page: int = Query(1, ge=1),
) -> CoreResponseDTO:
    """
    Получение состояния боя (Snapshot) или логов.
    """
    params = {"page": page}
    return await gateway.get_view(char_id, view_type, params)
