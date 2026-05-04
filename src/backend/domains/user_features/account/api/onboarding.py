from typing import Any

from fastapi import APIRouter, Body, Depends

from src.backend.dependencies.features.account import get_onboarding_gateway
from src.backend.domains.user_features.account.gateway.onboarding_gateway import OnboardingGateway
from src.shared.schemas.response import CoreResponseDTO

router = APIRouter(tags=["Account Onboarding"])


@router.post("/{char_id}/action", response_model=CoreResponseDTO)
async def handle_action(
    char_id: int,
    action: str = Body(..., embed=True),  # Ожидает {"action": "..."}
    value: Any = Body(None, embed=True),  # Ожидает {"value": "..."}
    gateway: OnboardingGateway = Depends(get_onboarding_gateway),
):
    """
    Обрабатывает действие онбординга.
    Принимает JSON: {"action": "set_name", "value": "Hero"}
    """
    return await gateway.handle_action(char_id, action, value)
