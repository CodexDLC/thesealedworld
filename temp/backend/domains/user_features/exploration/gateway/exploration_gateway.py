# backend/domains/user_features/exploration/gateway/exploration_gateway.py
"""
Gateway (фасад) для домена Exploration.
Точка входа для API/Dispatcher.
Упаковывает результаты в CoreResponseDTO.
"""

from typing import Any

from loguru import logger as log

from src.backend.domains.user_features.exploration.services.exploration_service import ExplorationService
from src.shared.schemas.exploration import EncounterDTO, ExplorationListDTO, WorldNavigationDTO
from src.shared.schemas.response import ServiceResult


class ExplorationGateway:
    """
    Фасад домена Exploration.
    """

    def __init__(self, exploration_service: ExplorationService):
        self._service = exploration_service

    # =========================================================================
    # 1. Move (Движение + Риск)
    # =========================================================================

    async def move(self, char_id: int, direction: str | None = None, target_id: str | None = None) -> dict[str, Any]:
        """
        Перемещение персонажа.
        Принимает target_id (предпочтительно) или direction (legacy).
        """
        # TODO: Return CoreResponseDTO directly instead of dict
        try:
            result = await self._service.move(char_id, direction, target_id)
            return self._wrap_result(result)
        except Exception as e:  # noqa: BLE001
            log.exception(f"ExplorationGateway | move_error char_id={char_id} target={target_id}")
            return self._error_response(f"Внутренняя ошибка: {e}")

    # =========================================================================
    # 2. Look Around (Безопасный обзор)
    # =========================================================================

    async def look_around(self, char_id: int) -> dict[str, Any]:
        """
        Обновление данных текущей локации.
        Безопасно (не вызывает энкаунтеры).
        """
        # TODO: Return CoreResponseDTO directly instead of dict
        try:
            result = await self._service.look_around(char_id)
            return self._wrap_result(result)
        except Exception as e:  # noqa: BLE001
            log.exception(f"ExplorationGateway | look_around_error char_id={char_id}")
            return self._error_response(f"Внутренняя ошибка: {e}")

    # =========================================================================
    # 3. Interact (Действия + Риск)
    # =========================================================================

    async def interact(self, char_id: int, action: str, target_id: str | None = None) -> dict[str, Any]:
        """
        Взаимодействие (Поиск, Сканирование, Объекты).
        Может вызвать энкаунтер (например, поиск).
        """
        # TODO: Return CoreResponseDTO directly instead of dict
        try:
            result = await self._service.interact(char_id, action, target_id)
            return self._wrap_result(result)
        except Exception as e:  # noqa: BLE001
            log.exception(f"ExplorationGateway | interact_error char_id={char_id} action={action}")
            return self._error_response(f"Внутренняя ошибка: {e}")

    # =========================================================================
    # 4. Use Service (Смена контекста)
    # =========================================================================

    async def use_service(self, char_id: int, service_id: str) -> dict[str, Any]:
        """
        Вход в сервис (переключение домена).
        """
        # TODO: Return CoreResponseDTO directly instead of dict
        try:
            # TODO: Проверка доступности сервиса
            return self._success_response({"target_service": service_id}, payload_type="redirect")
        except Exception as e:  # noqa: BLE001
            log.exception(f"ExplorationGateway | use_service_error char_id={char_id} service={service_id}")
            return self._error_response(f"Внутренняя ошибка: {e}")

    # =========================================================================
    # Helpers
    # =========================================================================

    def _wrap_result(self, result: Any) -> dict[str, Any]:
        """
        Определяет тип результата и упаковывает его.
        """
        # TODO: Refactor to return CoreResponseDTO

        # ServiceResult → переход в другой домен
        if isinstance(result, ServiceResult):
            return self._state_transition_response(result)

        if isinstance(result, EncounterDTO):
            return self._success_response(result, payload_type="encounter")

        if isinstance(result, WorldNavigationDTO):
            return self._success_response(result, payload_type="navigation")

        if isinstance(result, ExplorationListDTO):
            return self._success_response(result, payload_type="list")

        if isinstance(result, dict):
            return self._success_response(result, payload_type="info")

        return self._error_response("Неизвестный результат операции.")

    @staticmethod
    def _success_response(data: Any, payload_type: str) -> dict[str, Any]:
        if hasattr(data, "model_dump"):
            data = data.model_dump()

        return {
            "success": True,
            "data": data,
            "error": None,
            "payload_type": payload_type,
        }

    @staticmethod
    def _state_transition_response(result: ServiceResult) -> dict[str, Any]:
        """
        Ответ с переходом в другой домен (например, COMBAT).
        """
        data = result.data
        if hasattr(data, "model_dump"):
            data = data.model_dump()

        return {
            "success": True,
            "data": data,
            "error": None,
            "payload_type": "state_transition",
            "next_state": result.next_state.value if result.next_state else None,
        }

    @staticmethod
    def _error_response(message: str) -> dict[str, Any]:
        return {
            "success": False,
            "data": None,
            "error": message,
            "payload_type": "error",
        }
