from fastapi import APIRouter

from src.backend.dependencies.features.scenario import ScenarioGatewayDep
from src.backend.dependencies.internal.dispatcher import SystemDispatcherDep
from src.shared.schemas.response import CoreResponseDTO
from src.shared.schemas.scenario import ScenarioInitDTO

router = APIRouter(prefix="/scenario", tags=["Scenario"])


@router.post("/initialize", response_model=CoreResponseDTO)
async def initialize_scenario(
    char_id: int,
    payload: ScenarioInitDTO,
    gateway: ScenarioGatewayDep,
) -> CoreResponseDTO:
    """
    Запуск нового сценария (квеста).
    """
    return await gateway.initialize_scenario(
        char_id=char_id,
        quest_key=payload.quest_key,
        prev_state=None,  # TODO: Get from request if needed
        prev_loc=None,  # TODO: Get from request if needed
    )


@router.post("/step", response_model=CoreResponseDTO)
async def step_scenario(
    char_id: int,
    action_id: str,
    gateway: ScenarioGatewayDep,
    dispatcher: SystemDispatcherDep,
) -> CoreResponseDTO:
    """
    Выполнение шага (нажатие кнопки).
    """
    return await gateway.step_scenario(char_id=char_id, action_id=action_id, dispatcher=dispatcher)
