# backend/domains/user_features/exploration/api/router.py

from fastapi import APIRouter, Query

from src.backend.dependencies.features.exploration import ExplorationGatewayDep
from src.shared.schemas.exploration import InteractRequest, MoveRequest, UseServiceRequest
from src.shared.schemas.response import CoreResponseDTO

router = APIRouter(prefix="/exploration", tags=["Exploration"])


# --- Endpoints ---


@router.post("/move", response_model=CoreResponseDTO)
async def move(request: MoveRequest, gateway: ExplorationGatewayDep) -> CoreResponseDTO:
    """
    Перемещение персонажа.
    """
    # TODO: Refactor Gateway to return CoreResponseDTO directly (Arena/Inventory style)
    result = await gateway.move(request.char_id, request.direction)
    return CoreResponseDTO(**result)


@router.get("/look_around", response_model=CoreResponseDTO)
async def look_around(
    gateway: ExplorationGatewayDep,
    char_id: int = Query(...),
) -> CoreResponseDTO:
    """
    Обзор локации.
    """
    # TODO: Refactor Gateway to return CoreResponseDTO directly
    result = await gateway.look_around(char_id)
    return CoreResponseDTO(**result)


@router.post("/interact", response_model=CoreResponseDTO)
async def interact(request: InteractRequest, gateway: ExplorationGatewayDep) -> CoreResponseDTO:
    """
    Взаимодействие (Поиск, Скан, Объекты).
    """
    # TODO: Refactor Gateway to return CoreResponseDTO directly
    result = await gateway.interact(request.char_id, request.action, request.target_id)
    return CoreResponseDTO(**result)


@router.post("/use_service", response_model=CoreResponseDTO)
async def use_service(request: UseServiceRequest, gateway: ExplorationGatewayDep) -> CoreResponseDTO:
    """
    Вход в сервис.
    """
    # TODO: Refactor Gateway to return CoreResponseDTO directly
    result = await gateway.use_service(request.char_id, request.service_id)
    return CoreResponseDTO(**result)
