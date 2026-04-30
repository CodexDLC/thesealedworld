from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_db
from src.backend.core.exceptions import BusinessLogicException
from src.backend.features.auth.dependencies import get_current_user
from src.backend.features.auth.models import User
from src.backend.features.scenario.dependencies import build_scenario_service
from src.backend.features.scenario.dto.finalize import ScenarioFinalizeResult
from src.backend.features.scenario.services import ScenarioService
from src.backend.infrastructure.db.actor_state.models import Character
from src.shared.enums import CoreDomain
from src.shared.schemas import CoreResponseDTO, GameStateHeader, ScenarioPayloadDTO

router = APIRouter(prefix="/scenario", tags=["Scenario"])


class ScenarioStepRequestDTO(BaseModel):
    char_id: int
    action_id: str


def get_scenario_service(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
) -> ScenarioService:
    return build_scenario_service(request, db_session)


@router.post("/step", response_model=CoreResponseDTO[ScenarioPayloadDTO | ScenarioFinalizeResult])
async def step_scenario(
    dto: ScenarioStepRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
    scenario_service: Annotated[ScenarioService, Depends(get_scenario_service)],
) -> CoreResponseDTO[ScenarioPayloadDTO | ScenarioFinalizeResult]:
    owner_id: Any = await db_session.scalar(select(Character.user_id).where(Character.character_id == dto.char_id))
    if owner_id != current_user.id:
        raise BusinessLogicException("Scenario character is unavailable")

    payload = await scenario_service.step(dto.char_id, dto.action_id)
    if isinstance(payload, ScenarioPayloadDTO):
        payload.extra_data = {**(payload.extra_data or {}), "char_id": dto.char_id}
        return CoreResponseDTO(
            header=GameStateHeader(current_state=CoreDomain.SCENARIO),
            payload=payload,
            payload_type="scenario_screen",
        )

    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.EXPLORATION, previous_state=CoreDomain.SCENARIO),
        payload=payload,
        payload_type="scenario_finalized",
    )
