from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.exceptions import BusinessLogicException, NotFoundException, PermissionDeniedException
from src.backend.database.postgres.repositories.characters_repo_orm import CharactersRepoORM
from src.backend.domains.user_features.account.services.account_session_service import AccountSessionService
from src.backend.domains.user_features.account.services.onboarding_service import OnboardingService
from src.shared.schemas.character import CharacterReadDTO, CharacterShellCreateDTO
from src.shared.schemas.onboarding import OnboardingUIPayloadDTO

MAX_CHARACTERS = 4


class LobbyService:
    """
    Сервис управления персонажами (Lobby).
    """

    def __init__(
        self, session: AsyncSession, session_service: AccountSessionService, onboarding_service: OnboardingService
    ):
        self.repo = CharactersRepoORM(session)
        self.session_service = session_service
        self.onboarding_service = onboarding_service

    async def get_characters_list(self, user_id: int) -> list[CharacterReadDTO]:
        """
        Получает список персонажей (Cache-Aside).
        """
        # 1. Try Cache
        cached_chars = await self.session_service.get_lobby_cache(user_id)
        if cached_chars is not None:
            return cached_chars

        # 2. Cache Miss -> DB
        characters = await self.repo.get_characters(user_id)

        if not characters:
            return []

        # 3. Save to Cache
        await self.session_service.set_lobby_cache(user_id, characters)

        return characters

    async def create_character_shell(self, user_id: int) -> OnboardingUIPayloadDTO:
        """
        Создает болванку персонажа и инициализирует онбординг.
        Возвращает Payload для первого шага онбординга.
        """
        # 1. Проверка лимита
        characters = await self.repo.get_characters(user_id)
        if len(characters) >= MAX_CHARACTERS:
            raise BusinessLogicException(f"Maximum {MAX_CHARACTERS} characters allowed")

        # 2. Создание в БД
        dto = CharacterShellCreateDTO(user_id=user_id)
        character_dto = await self.repo.create_character_shell(dto)

        # 3. Инициализация Onboarding
        payload = await self.onboarding_service.initialize(character_dto)

        # 4. Инвалидация кэша лобби
        await self.session_service.delete_lobby_cache(user_id)

        return payload

    async def delete_character(self, char_id: int, user_id: int) -> bool:
        """
        Удаляет персонажа.
        """
        # 1. Проверка существования и владельца
        character = await self.repo.get_character(char_id)
        if not character:
            raise NotFoundException(f"Character {char_id} not found")

        if character.user_id != user_id:
            raise PermissionDeniedException("You are not the owner of this character")

        # 2. Удаление
        await self.repo.delete_characters(char_id)
        await self.session_service.delete_lobby_cache(user_id)
        return True
