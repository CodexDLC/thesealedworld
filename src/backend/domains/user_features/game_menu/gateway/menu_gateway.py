from typing import Any

from loguru import logger

from src.backend.core.exceptions import SessionExpiredException
from src.backend.domains.user_features.game_menu.services.game_menu_service import GameMenuService
from src.shared.enums.domain_enums import CoreDomain
from src.shared.schemas.game_menu import GameMenuDTO
from src.shared.schemas.response import CoreResponseDTO, GameStateHeader


class GameMenuGateway:
    """
    Gateway для Game Menu.
    Оборачивает ответы сервиса в CoreResponseDTO и обрабатывает исключения.
    """

    def __init__(self, service: GameMenuService):
        self.service = service

    async def get_view(self, char_id: int) -> CoreResponseDTO[GameMenuDTO]:
        try:
            menu_dto = await self.service.get_menu_view(char_id)

            # Получаем стейт для хедера
            current_state = await self.service.session.get_current_state(char_id)

            return CoreResponseDTO(
                header=GameStateHeader(
                    current_state=current_state,  # type: ignore
                ),
                payload=menu_dto,
            )

        except SessionExpiredException:
            return self._create_session_expired_response()
        except (KeyError, ValueError, TypeError) as e:
            logger.exception(f"Error in get_view for char_id {char_id}: {e}")
            return self._create_error_response(str(e))

    async def dispatch_action(self, char_id: int, action_id: str) -> CoreResponseDTO[Any]:
        try:
            return await self.service.process_menu_action(char_id, action_id)
        except SessionExpiredException:
            return self._create_session_expired_response()
        except (KeyError, ValueError, TypeError) as e:
            logger.exception(f"Error in dispatch_action for char_id {char_id}, action {action_id}: {e}")
            return self._create_error_response(str(e))

    def _create_session_expired_response(self) -> CoreResponseDTO[Any]:
        return CoreResponseDTO(
            header=GameStateHeader(current_state=CoreDomain.LOBBY, error="session_expired"), payload={}
        )

    def _create_error_response(self, msg: str) -> CoreResponseDTO[Any]:
        return CoreResponseDTO(
            header=GameStateHeader(
                current_state=CoreDomain.LOBBY,  # Fallback to Lobby on critical error
                error=f"internal_error: {msg}",
            ),
            payload={},
        )
