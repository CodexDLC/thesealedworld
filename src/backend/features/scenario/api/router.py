from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.config.settings import settings
from src.backend.core.database import get_db
from src.backend.features.scenario.dependencies import build_scenario_service
from src.backend.features.scenario.services import ScenarioService
from src.backend.features_site.auth.dependencies import get_current_user
from src.backend.features_site.auth.models import User
from src.shared.enums import CoreDomain
from src.shared.schemas import CoreResponseDTO, GameStateHeader, ScenarioPayloadDTO, StateTransitionDTO
from src.shared.utils.dev_utils import log_debug_payload

router = APIRouter(prefix="/scenario", tags=["Scenario"])


class ScenarioStepRequestDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    char_id: int
    action_id: str

    @field_validator("action_id")
    @classmethod
    def validate_action_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("action_id cannot be empty")
        return v


class ScenarioInitializeRequestDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    char_id: int
    quest_key: str

    @field_validator("quest_key")
    @classmethod
    def validate_quest_key(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("quest_key cannot be empty")
        return v


def get_scenario_service(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
) -> ScenarioService:
    return build_scenario_service(request, db_session)


@router.post("/initialize", response_model=CoreResponseDTO[ScenarioPayloadDTO])
async def initialize_scenario(
    dto: ScenarioInitializeRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    scenario_service: Annotated[ScenarioService, Depends(get_scenario_service)],
) -> CoreResponseDTO[ScenarioPayloadDTO]:
    await scenario_service.ensure_character_owner(user_id=current_user.id, char_id=dto.char_id)
    payload = await scenario_service.initialize(dto.char_id, dto.quest_key, source="api")
    payload.extra_data = {**(payload.extra_data or {}), "char_id": dto.char_id, "quest_key": dto.quest_key}
    response = CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.SCENARIO),
        payload=payload,
        payload_type="scenario_screen",
    )
    log_debug_payload("scenario.initialize", response, enabled=settings.debug)
    return response


@router.get("/resume/{char_id}", response_model=CoreResponseDTO[ScenarioPayloadDTO])
async def resume_scenario(
    char_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    scenario_service: Annotated[ScenarioService, Depends(get_scenario_service)],
) -> CoreResponseDTO[ScenarioPayloadDTO]:
    await scenario_service.ensure_character_owner(user_id=current_user.id, char_id=char_id)
    payload = await scenario_service.resume(char_id)
    payload.extra_data = {**(payload.extra_data or {}), "char_id": char_id}
    response = CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.SCENARIO),
        payload=payload,
        payload_type="scenario_screen",
    )
    log_debug_payload("scenario.resume", response, enabled=settings.debug)
    return response


@router.post("/step", response_model=CoreResponseDTO[ScenarioPayloadDTO | StateTransitionDTO])
async def step_scenario(
    dto: ScenarioStepRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    scenario_service: Annotated[ScenarioService, Depends(get_scenario_service)],
) -> CoreResponseDTO[ScenarioPayloadDTO | StateTransitionDTO]:
    await scenario_service.ensure_character_owner(user_id=current_user.id, char_id=dto.char_id)

    payload = await scenario_service.step(dto.char_id, dto.action_id)
    if isinstance(payload, ScenarioPayloadDTO):
        payload.extra_data = {**(payload.extra_data or {}), "char_id": dto.char_id}
        response: CoreResponseDTO[ScenarioPayloadDTO | StateTransitionDTO] = CoreResponseDTO(
            header=GameStateHeader(current_state=CoreDomain.SCENARIO),
            payload=payload,
            payload_type="scenario_screen",
        )
        log_debug_payload("scenario.step", response, enabled=settings.debug)
        return response

    transition = StateTransitionDTO(
        char_id=dto.char_id,
        target_state=payload.target_state,
        reason=payload.transition_reason,
        combat_id=payload.combat_id,
        location_id=payload.location_id,
        metadata={
            "rewards": payload.rewards.model_dump(mode="json"),
            **payload.metadata,
        },
    )
    response = CoreResponseDTO(
        header=GameStateHeader(current_state=payload.target_state, previous_state=CoreDomain.SCENARIO),
        payload=transition,
        payload_type="state_transition",
    )
    log_debug_payload("scenario.step", response, enabled=settings.debug)
    return response
