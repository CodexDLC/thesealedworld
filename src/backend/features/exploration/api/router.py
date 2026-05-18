from typing import Any, cast

from fastapi import APIRouter, Query

from src.backend.features.exploration.dependencies import ExplorationGatewayDep
from src.shared.schemas.exploration import (
    EncounterDTO,
    ExplorationListDTO,
    ExplorationLocalMapDTO,
    ExplorationScreenDTO,
    InteractRequest,
    MoveRequest,
    UseServiceRequest,
    WorldNavigationDTO,
)
from src.shared.schemas.response import CoreResponseDTO, StateTransitionDTO

router = APIRouter(prefix="/exploration", tags=["Exploration"])

ExplorationPayload = (
    ExplorationScreenDTO | WorldNavigationDTO | EncounterDTO | ExplorationListDTO | StateTransitionDTO | dict[str, Any]
)


@router.post("/move", response_model=CoreResponseDTO[ExplorationPayload])
async def move(request: MoveRequest, gateway: ExplorationGatewayDep) -> CoreResponseDTO[ExplorationPayload]:
    """
    Перемещение персонажа между локациями.
    """
    return cast(
        "CoreResponseDTO[ExplorationPayload]", await gateway.move(request.char_id, request.direction, request.target_id)
    )


@router.get("/look_around", response_model=CoreResponseDTO[ExplorationPayload])
async def look_around(
    gateway: ExplorationGatewayDep,
    char_id: int = Query(...),
) -> CoreResponseDTO[ExplorationPayload]:
    """
    Обзор текущей локации (обновление данных).
    """
    return cast("CoreResponseDTO[ExplorationPayload]", await gateway.look_around(char_id))


@router.get("/local_map", response_model=ExplorationLocalMapDTO)
async def local_map(
    gateway: ExplorationGatewayDep,
    char_id: int = Query(...),
    radius: int = Query(2, ge=1, le=4),
) -> ExplorationLocalMapDTO:
    """
    Local map area centered on the player's current location.
    """
    return await gateway.local_map(char_id, radius=radius)


@router.post("/interact", response_model=CoreResponseDTO[ExplorationPayload])
async def interact(request: InteractRequest, gateway: ExplorationGatewayDep) -> CoreResponseDTO[ExplorationPayload]:
    """
    Взаимодействие с объектами или реакция на события (Attack, Bypass, Search).
    """
    return cast(
        "CoreResponseDTO[ExplorationPayload]",
        await gateway.interact(request.char_id, request.action, request.target_id),
    )


@router.post("/use_service", response_model=CoreResponseDTO[ExplorationPayload])
async def use_service(
    request: UseServiceRequest, gateway: ExplorationGatewayDep
) -> CoreResponseDTO[ExplorationPayload]:
    """
    Вход в сервис (Здания, Магазины).
    """
    return cast("CoreResponseDTO[ExplorationPayload]", await gateway.use_service(request.char_id, request.service_id))
