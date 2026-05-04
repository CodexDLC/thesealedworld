from typing import Any

from loguru import logger

from src.backend.domains.user_features.arena.services.arena_service import ArenaService
from src.shared.enums.domain_enums import CoreDomain
from src.shared.schemas.arena import ArenaActionEnum, ArenaUIPayloadDTO
from src.shared.schemas.response import CoreResponseDTO, GameStateHeader


class ArenaGateway:
    def __init__(self, service: ArenaService):
        self.service = service

    async def handle_action(self, char_id: int, action: str, mode: str | None, value: Any) -> CoreResponseDTO:
        """
        Главная точка входа. Маршрутизирует по action.
        """
        try:
            # action routing:
            if action == ArenaActionEnum.MENU_MAIN.value:
                return self._success(await self.service.get_main_menu())

            elif action == ArenaActionEnum.MENU_MODE.value:
                if not mode:
                    return self._error("Mode is required")
                return self._success(await self.service.get_mode_menu(mode))

            elif action == ArenaActionEnum.JOIN_QUEUE.value:
                if not mode:
                    return self._error("Mode is required")
                return self._success(await self.service.join_queue(char_id, mode))

            elif action == ArenaActionEnum.CHECK_MATCH.value:
                if not mode:
                    return self._error("Mode is required")

                result = await self.service.check_match(char_id, mode)

                if isinstance(result, str):
                    if result == "combat":
                        return self._redirect(CoreDomain.COMBAT)
                    return self._error(f"Unknown service result: {result}")

                return self._success(result)

            elif action == ArenaActionEnum.CANCEL_QUEUE.value:
                if not mode:
                    return self._error("Mode is required")
                return self._success(await self.service.cancel_queue(char_id, mode))

            elif action == ArenaActionEnum.LEAVE.value:
                return self._redirect(CoreDomain.LOBBY)

            logger.warning(f"ArenaGateway | Unknown action: {action} for char_id={char_id}")
            return self._error(f"Unknown action: {action}")

        except Exception as e:  # noqa: BLE001
            logger.exception(f"ArenaGateway | Error handling action '{action}' for char_id={char_id}: {e}")
            return self._error("Internal Arena Error")

    def _success(self, payload: ArenaUIPayloadDTO) -> CoreResponseDTO:
        return CoreResponseDTO(header=GameStateHeader(current_state=CoreDomain.ARENA), payload=payload)

    def _redirect(self, target: CoreDomain, payload: Any = None) -> CoreResponseDTO:
        return CoreResponseDTO(header=GameStateHeader(current_state=target), payload=payload)

    def _error(self, message: str) -> CoreResponseDTO:
        return CoreResponseDTO(header=GameStateHeader(current_state=CoreDomain.ARENA, error=message), payload=None)
