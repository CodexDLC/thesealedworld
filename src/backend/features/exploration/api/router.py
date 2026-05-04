from typing import Any

from fastapi import APIRouter, Query

from src.backend.features.exploration.dependencies import ExplorationServiceDep
from src.shared.enums import CoreDomain
from src.shared.schemas.exploration import (
    EncounterDTO,
    ExplorationListDTO,
    InteractRequest,
    MoveRequest,
    UseServiceRequest,
    WorldNavigationDTO,
)
from src.shared.schemas.response import CoreResponseDTO, GameStateHeader, ServiceResult, StateTransitionDTO

router = APIRouter(prefix="/exploration", tags=["Exploration"])

ExplorationPayload = WorldNavigationDTO | EncounterDTO | ExplorationListDTO | StateTransitionDTO | dict[str, Any]


@router.post("/move", response_model=CoreResponseDTO[ExplorationPayload])
async def move(request: MoveRequest, service: ExplorationServiceDep) -> CoreResponseDTO[ExplorationPayload]:
    """
    Перемещение персонажа между локациями.
    """
    result = await service.move(request.char_id, request.direction, request.target_id)
    return _exploration_response(result)


@router.get("/look_around", response_model=CoreResponseDTO[ExplorationPayload])
async def look_around(
    service: ExplorationServiceDep,
    char_id: int = Query(...),
) -> CoreResponseDTO[ExplorationPayload]:
    """
    Обзор текущей локации (обновление данных).
    """
    result = await service.look_around(char_id)
    return _exploration_response(result)


@router.post("/interact", response_model=CoreResponseDTO[ExplorationPayload])
async def interact(request: InteractRequest, service: ExplorationServiceDep) -> CoreResponseDTO[ExplorationPayload]:
    """
    Взаимодействие с объектами или реакция на события (Attack, Bypass, Search).
    """
    result = await service.interact(request.char_id, request.action, request.target_id)

    if isinstance(result, ServiceResult):
        current_state = result.next_state or CoreDomain.EXPLORATION
        previous_state = CoreDomain.EXPLORATION if current_state != CoreDomain.EXPLORATION else None
        payload: Any = result.data
        payload_type = _payload_type(payload, current_state=current_state)
        if current_state != CoreDomain.EXPLORATION:
            payload = StateTransitionDTO(
                char_id=request.char_id,
                target_state=current_state,
                reason=f"exploration_{request.action}",
                combat_id=payload.get("combat_id") if isinstance(payload, dict) else None,
                metadata=payload if isinstance(payload, dict) else {},
            )
            payload_type = "state_transition"
        return CoreResponseDTO(
            header=GameStateHeader(current_state=current_state, previous_state=previous_state),
            payload=payload,
            payload_type=payload_type,
        )

    return _exploration_response(result)


@router.post("/use_service", response_model=CoreResponseDTO[ExplorationPayload])
async def use_service(
    request: UseServiceRequest, service: ExplorationServiceDep
) -> CoreResponseDTO[ExplorationPayload]:
    """
    Вход в сервис (Здания, Магазины).
    """
    result = await service.use_service(request.char_id, request.service_id)
    if isinstance(result, ServiceResult):
        current_state = result.next_state or CoreDomain.EXPLORATION
        payload = StateTransitionDTO(
            char_id=request.char_id,
            target_state=current_state,
            reason="exploration_service_entry",
            metadata=result.data if isinstance(result.data, dict) else {},
        )
        return CoreResponseDTO(
            header=GameStateHeader(current_state=current_state, previous_state=CoreDomain.EXPLORATION),
            payload=payload,
            payload_type="state_transition",
        )
    return _exploration_response(result)


def _exploration_response(
    payload: ExplorationPayload,
    *,
    payload_type: str | None = None,
) -> CoreResponseDTO[ExplorationPayload]:
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.EXPLORATION),
        payload=payload,
        payload_type=payload_type or _payload_type(payload),
    )


def _payload_type(payload: Any, *, current_state: CoreDomain = CoreDomain.EXPLORATION) -> str:
    if current_state == CoreDomain.COMBAT:
        return "combat_transition"
    if isinstance(payload, WorldNavigationDTO):
        return "exploration_navigation"
    if isinstance(payload, EncounterDTO):
        return "exploration_encounter"
    if isinstance(payload, ExplorationListDTO):
        return "exploration_list"
    return "exploration_payload"
