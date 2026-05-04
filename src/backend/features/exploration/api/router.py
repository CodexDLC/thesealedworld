# src/backend/features/exploration/api/router.py
from fastapi import APIRouter, Query

from src.backend.features.exploration.dependencies import ExplorationServiceDep
from src.shared.schemas.exploration import InteractRequest, MoveRequest, UseServiceRequest
from src.shared.schemas.response import CoreResponseDTO, ServiceResult

router = APIRouter(prefix="/exploration", tags=["Exploration"])


@router.post("/move", response_model=CoreResponseDTO)
async def move(request: MoveRequest, service: ExplorationServiceDep) -> CoreResponseDTO:
    """
    Перемещение персонажа между локациями.
    """
    result = await service.move(request.char_id, request.direction, request.target_id)
    
    if isinstance(result, CoreResponseDTO):
        return result
    
    return CoreResponseDTO(data=result)


@router.get("/look_around", response_model=CoreResponseDTO)
async def look_around(
    service: ExplorationServiceDep,
    char_id: int = Query(...),
) -> CoreResponseDTO:
    """
    Обзор текущей локации (обновление данных).
    """
    result = await service.look_around(char_id)
    return CoreResponseDTO(data=result)


@router.post("/interact", response_model=CoreResponseDTO)
async def interact(request: InteractRequest, service: ExplorationServiceDep) -> CoreResponseDTO:
    """
    Взаимодействие с объектами или реакция на события (Attack, Bypass, Search).
    """
    result = await service.interact(request.char_id, request.action, request.target_id)
    
    if isinstance(result, ServiceResult):
        return CoreResponseDTO(data=result.data, next_state=result.next_state)
    
    return CoreResponseDTO(data=result)


@router.post("/use_service", response_model=CoreResponseDTO)
async def use_service(request: UseServiceRequest, service: ExplorationServiceDep) -> CoreResponseDTO:
    """
    Вход в сервис (Здания, Магазины).
    """
    # TODO: Implement service entry logic in ExplorationService
    return CoreResponseDTO(data={"message": "Service entry not implemented yet"})
