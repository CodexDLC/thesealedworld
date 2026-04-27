from src.backend.core.exceptions import BaseAPIException
from src.backend.domains.user_features.account.services.lobby_service import LobbyService
from src.shared.enums.domain_enums import CoreDomain
from src.shared.schemas.lobby import LobbyListDTO
from src.shared.schemas.onboarding import OnboardingUIPayloadDTO
from src.shared.schemas.response import CoreResponseDTO, GameStateHeader


class LobbyGateway:
    """
    Gateway для Lobby.
    """

    def __init__(self, service: LobbyService):
        self.service = service

    # ==========================================================================
    # PUBLIC API (CoreResponseDTO Wrapper)
    # ==========================================================================

    async def initialize(self, user_id: int) -> CoreResponseDTO:
        """
        Вход в лобби.
        Если персонажей нет -> Создает нового и возвращает ONBOARDING.
        Если персонажи есть -> Возвращает LOBBY.
        """
        try:
            # 1. Получаем список
            characters = await self.service.get_characters_list(user_id)

            if not characters:
                # 2. Авто-создание (возвращает OnboardingUIPayloadDTO)
                payload = await self.service.create_character_shell(user_id)
                return CoreResponseDTO(header=GameStateHeader(current_state=CoreDomain.ONBOARDING), payload=payload)

            # 3. Возвращаем список
            return CoreResponseDTO(
                header=GameStateHeader(current_state=CoreDomain.LOBBY), payload=LobbyListDTO(characters=characters)
            )
        except BaseAPIException as e:
            return self._error_response(e.detail)
        except Exception as e:  # noqa: BLE001
            return self._error_response(f"Initialize failed: {e}")

    async def list_characters(self, user_id: int) -> CoreResponseDTO[LobbyListDTO]:
        """
        Ручка для API: Получить список (без авто-создания).
        """
        try:
            characters = await self.service.get_characters_list(user_id)
            return CoreResponseDTO(
                header=GameStateHeader(current_state=CoreDomain.LOBBY), payload=LobbyListDTO(characters=characters)
            )
        except Exception as e:  # noqa: BLE001
            return self._error_response(str(e))

    async def create_character(self, user_id: int) -> CoreResponseDTO[OnboardingUIPayloadDTO]:
        """
        Ручка для API: Создать персонажа.
        """
        try:
            payload = await self.service.create_character_shell(user_id)
            return CoreResponseDTO(header=GameStateHeader(current_state=CoreDomain.ONBOARDING), payload=payload)
        except BaseAPIException as e:
            return self._error_response(e.detail)
        except Exception as e:  # noqa: BLE001
            return self._error_response(f"Create failed: {e}")

    async def delete_character(self, char_id: int, user_id: int) -> CoreResponseDTO:
        """
        Ручка для API: Удалить персонажа.
        """
        try:
            await self.service.delete_character(char_id, user_id)
            # Возвращаем обновленный список
            return await self.list_characters(user_id)
        except BaseAPIException as e:
            return self._error_response(e.detail)
        except Exception as e:  # noqa: BLE001
            return self._error_response(f"Delete failed: {e}")

    # ==========================================================================
    # INTERNAL LOGIC
    # ==========================================================================

    def _error_response(self, message: str) -> CoreResponseDTO:
        return CoreResponseDTO(header=GameStateHeader(current_state=CoreDomain.LOBBY, error=message), payload=None)
