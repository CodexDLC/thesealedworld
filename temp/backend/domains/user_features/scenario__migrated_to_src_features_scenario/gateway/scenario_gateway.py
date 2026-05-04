# backend/domains/user_features/scenario/gateway/scenario_gateway.py
from typing import TYPE_CHECKING, Any

from src.backend.domains.user_features.scenario.service.scenario_service import ScenarioService
from src.shared.enums.domain_enums import CoreDomain
from src.shared.schemas.response import CoreResponseDTO, GameStateHeader
from src.shared.schemas.scenario import ScenarioPayloadDTO

if TYPE_CHECKING:
    from src.backend.domains.internal_systems.dispatcher.system_dispatcher import SystemDispatcher


class ScenarioGateway:
    """
    Точка входа в домен Scenario.
    Реализует два контракта:
    1. Для SystemDispatcher (get_entry_point): возвращает чистый Payload.
    2. Для API (public methods): возвращает CoreResponseDTO.
    """

    def __init__(self, service: ScenarioService):
        self.service = service

    # --- 1. For SystemDispatcher (Internal, returns Payload) ---

    async def get_entry_point(self, char_id: int, action: str, context: dict[str, Any]) -> ScenarioPayloadDTO:
        """
        Единая точка входа для междоменного взаимодействия.
        Возвращает PayloadDTO.
        """
        if action == "initialize":
            return await self.service.initialize_payload(
                char_id, context.get("quest_key", ""), context.get("prev_state"), context.get("prev_loc")
            )
        elif action == "resume":
            return await self.service.resume_payload(char_id)

        raise ValueError(f"Unknown entry action for Scenario: {action}")

    # --- 2. For API Router (External, returns CoreResponseDTO) ---

    async def initialize_scenario(
        self, char_id: int, quest_key: str, prev_state: str | None = None, prev_loc: str | None = None
    ) -> CoreResponseDTO:
        """Вызывается API. Возвращает CoreResponseDTO."""
        payload = await self.service.initialize_payload(char_id, quest_key, prev_state, prev_loc)
        return CoreResponseDTO(header=GameStateHeader(current_state=CoreDomain.SCENARIO), payload=payload)

    async def resume_scenario(self, char_id: int) -> CoreResponseDTO:
        """Вызывается API. Возвращает CoreResponseDTO."""
        payload = await self.service.resume_payload(char_id)
        return CoreResponseDTO(header=GameStateHeader(current_state=CoreDomain.SCENARIO), payload=payload)

    async def step_scenario(self, char_id: int, action_id: str, dispatcher: "SystemDispatcher") -> CoreResponseDTO:
        """
        Вызывается API. Возвращает CoreResponseDTO.
        Принимает dispatcher для обработки переходов.
        """
        # Передаем dispatcher в сервис
        result = await self.service.step_payload(char_id, action_id, dispatcher)

        # Если сервис вернул кортеж (Domain, Payload) -> это финализация и переход
        if isinstance(result, tuple):
            target_domain, payload = result

            # Payload уже готов (его вернул Хендлер через Диспетчер)
            # Просто упаковываем его
            return CoreResponseDTO(header=GameStateHeader(current_state=target_domain), payload=payload)

        # Иначе это обычный шаг внутри сценария
        return CoreResponseDTO(header=GameStateHeader(current_state=CoreDomain.SCENARIO), payload=result)
