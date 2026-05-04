from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.exceptions import NotFoundException, PermissionDeniedException
from src.backend.database.postgres.repositories.characters_repo_orm import CharactersRepoORM
from src.backend.domains.user_features.account.services.account_session_service import AccountSessionService
from src.shared.enums.domain_enums import CoreDomain
from src.shared.schemas.account_context import AccountContextDTO
from src.shared.schemas.character import CharacterReadDTO


class LoginService:
    """
    Сервис входа в игру (Login).
    Отвечает за восстановление/создание сессии и определение текущего состояния.
    """

    def __init__(self, session: AsyncSession, session_service: AccountSessionService):
        self.repo = CharactersRepoORM(session)
        self.session_service = session_service

    async def login(self, char_id: int, user_id: int) -> AccountContextDTO:
        """
        Вход персонажем.
        1. Проверяет владельца.
        2. Проверяет/создает сессию в Redis.
        3. Возвращает контекст.
        """
        # 1. Проверка существования и владельца (через БД, так как это критично)
        character = await self.repo.get_character(char_id)
        if not character:
            raise NotFoundException(f"Character {char_id} not found")

        if character.user_id != user_id:
            raise PermissionDeniedException("You are not the owner of this character")

        # 2. Проверка сессии в Redis
        context = await self.session_service.get_session(char_id)

        if context:
            # Сессия есть - возвращаем
            return context

        # 3. Сессии нет - восстанавливаем из БД

        # Определяем начальный стейт по game_stage из БД
        initial_state_str = character.game_stage

        try:
            # Пытаемся конвертировать строку из БД в Enum
            # Если в БД "creation", мапим на ONBOARDING
            initial_state = CoreDomain.ONBOARDING if initial_state_str == "creation" else CoreDomain(initial_state_str)
        except ValueError:
            # Если значение неизвестно, логируем и ставим дефолт (SCENARIO)
            log.warning(
                f"LoginService | Unknown game_stage '{initial_state_str}' for char {char_id}. Defaulting to SCENARIO."
            )
            initial_state = CoreDomain.SCENARIO

        # Создаем сессию
        # Используем CharacterReadDTO
        char_dto = CharacterReadDTO.model_validate(character)

        context = await self.session_service.create_session(char_dto, initial_state)

        return context
