from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.postgres.repositories.users_repo_orm import UsersRepoORM
from src.shared.schemas.user import UserDTO, UserUpsertDTO


class RegistrationService:
    """
    Сервис регистрации пользователей.
    """

    def __init__(self, session: AsyncSession):
        self.repo = UsersRepoORM(session)

    async def upsert_user(self, user_dto: UserUpsertDTO) -> UserDTO:
        """
        Создает или обновляет пользователя в БД и возвращает актуальные данные.
        """
        return await self.repo.upsert_user(user_dto)
