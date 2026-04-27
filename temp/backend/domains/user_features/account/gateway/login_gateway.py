from src.backend.core.exceptions import BaseAPIException
from src.backend.domains.internal_systems.dispatcher.system_dispatcher import SystemDispatcher
from src.backend.domains.user_features.account.gateway.onboarding_gateway import OnboardingGateway
from src.backend.domains.user_features.account.services.login_service import LoginService
from src.shared.enums.domain_enums import CoreDomain
from src.shared.schemas.response import CoreResponseDTO, GameStateHeader


class LoginGateway:
    """
    Gateway для входа.
    Оркестрирует процесс входа и перенаправляет в нужный домен.
    """

    def __init__(self, service: LoginService, onboarding_gateway: OnboardingGateway, dispatcher: SystemDispatcher):
        self.service = service
        self.onboarding_gateway = onboarding_gateway
        self.dispatcher = dispatcher

    async def login(self, char_id: int, user_id: int) -> CoreResponseDTO:
        """
        Вход в игру.
        Возвращает состояние и (опционально) Payload для отрисовки.
        """
        try:
            # 1. Логин в сервисе (получаем контекст)
            context = await self.service.login(char_id, user_id)
            state = context.state
            sessions = context.sessions  # SessionsDict (TypedDict)

            # 2. Роутинг по состоянию (State Machine)

            # --- 1. ONBOARDING ---
            if state == CoreDomain.ONBOARDING:
                return await self.onboarding_gateway.resume(char_id)

            # --- 2. COMBAT ---
            elif state == CoreDomain.COMBAT:
                try:
                    payload = await self.dispatcher.route(
                        domain=CoreDomain.COMBAT,
                        char_id=char_id,
                        action="resume",
                        context={"char_id": char_id, "sessions": sessions},
                    )
                    return CoreResponseDTO(header=GameStateHeader(current_state=CoreDomain.COMBAT), payload=payload)
                except Exception as e:  # noqa: BLE001
                    return self._error_response(f"Failed to load COMBAT: {e}")

            # --- 3. SCENARIO ---
            elif state == CoreDomain.SCENARIO:
                try:
                    payload = await self.dispatcher.route(
                        domain=CoreDomain.SCENARIO,
                        char_id=char_id,
                        action="resume",
                        context={"char_id": char_id, "sessions": sessions},
                    )
                    return CoreResponseDTO(header=GameStateHeader(current_state=CoreDomain.SCENARIO), payload=payload)
                except Exception as e:  # noqa: BLE001
                    return self._error_response(f"Failed to load SCENARIO: {e}")

            # --- 4. EXPLORATION (DEFAULT) ---
            else:
                try:
                    payload = await self.dispatcher.route(
                        domain=CoreDomain.EXPLORATION,
                        char_id=char_id,
                        action="resume",
                        context={"char_id": char_id, "sessions": sessions},
                    )
                    return CoreResponseDTO(
                        header=GameStateHeader(current_state=CoreDomain.EXPLORATION), payload=payload
                    )
                except Exception as e:  # noqa: BLE001
                    return self._error_response(f"Failed to load EXPLORATION: {e}")

        except BaseAPIException as e:
            return self._error_response(e.detail)
        except Exception as e:  # noqa: BLE001
            return self._error_response(f"Login failed: {e}")

    @staticmethod
    def _error_response(message: str) -> CoreResponseDTO:
        return CoreResponseDTO(header=GameStateHeader(current_state=CoreDomain.LOBBY, error=message), payload=None)
