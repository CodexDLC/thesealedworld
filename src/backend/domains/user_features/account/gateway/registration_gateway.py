from loguru import logger

from src.backend.core.exceptions import BaseAPIException
from src.backend.domains.user_features.account.services.registration_service import RegistrationService
from src.shared.enums.domain_enums import CoreDomain
from src.shared.schemas.response import CoreResponseDTO, GameStateHeader
from src.shared.schemas.user import UserDTO, UserUpsertDTO


class RegistrationGateway:
    """
    Gateway для регистрации.
    """

    def __init__(self, service: RegistrationService):
        self.service = service

    async def upsert_user(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        language_code: str | None = "ru",
        is_premium: bool = False,
    ) -> CoreResponseDTO[UserDTO]:
        dto = UserUpsertDTO(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            is_premium=is_premium,
        )

        try:
            user_dto = await self.service.upsert_user(dto)
            return CoreResponseDTO(header=GameStateHeader(current_state=CoreDomain.LOBBY), payload=user_dto)
        except BaseAPIException as e:
            logger.warning(f"Registration business error: {e.detail}")
            return CoreResponseDTO(
                header=GameStateHeader(current_state=CoreDomain.LOBBY, error=str(e.detail)), payload=None
            )
        except Exception:  # noqa: BLE001
            logger.exception(f"Registration failed for user {telegram_id}")
            return CoreResponseDTO(
                header=GameStateHeader(current_state=CoreDomain.LOBBY, error="Internal registration error"),
                payload=None,
            )
