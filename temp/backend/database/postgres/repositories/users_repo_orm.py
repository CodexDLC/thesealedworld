from typing import Any

from loguru import logger as log
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.database.db_contract.i_users_repo import IUserRepo
from src.backend.database.postgres.models.user import User
from src.shared.schemas.user import UserDTO, UserUpsertDTO


class UsersRepoORM(IUserRepo):
    """
    ORM-реализация репозитория для управления пользователями.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        log.debug(f"UsersRepoORM | status=initialized session={session}")

    async def upsert_user(self, user_data: UserUpsertDTO) -> UserDTO:
        """
        Создает или обновляет пользователя и возвращает актуальные данные.

        Args:
            user_data: DTO с данными пользователя.

        Returns:
            UserDTO: Актуальные данные пользователя.
        """
        user_data_dict = user_data.model_dump()
        orm_user = User(**user_data_dict)
        log.debug(f"UsersRepoORM | action=upsert_user telegram_id={orm_user.telegram_id}")

        try:
            # merge возвращает присоединенный экземпляр с актуальными данными (включая defaults)
            merged_user = await self.session.merge(orm_user)
            await self.session.flush()  # Чтобы получить ID и created_at, если это insert

            log.info(f"UsersRepoORM | action=upsert_user status=success telegram_id={merged_user.telegram_id}")
            return UserDTO.model_validate(merged_user)

        except SQLAlchemyError as e:
            log.exception(
                f"UsersRepoORM | action=upsert_user status=failed telegram_id={orm_user.telegram_id} error={e}"
            )
            raise

    async def get_user(self, telegram_id: int) -> UserDTO | None:
        """
        Получает пользователя по Telegram ID.

        Args:
            telegram_id: ID пользователя в Telegram.

        Returns:
            UserDTO | None: Данные пользователя или None, если не найден.
        """
        log.debug(f"UsersRepoORM | action=get_user telegram_id={telegram_id}")
        stmt = select(User).where(User.telegram_id == telegram_id)

        try:
            result = await self.session.execute(stmt)
            orm_user: User | None = result.scalar_one_or_none()

            if orm_user:
                log.debug(f"UsersRepoORM | action=get_user status=found telegram_id={telegram_id}")
                return UserDTO.model_validate(orm_user)
            else:
                log.debug(f"UsersRepoORM | action=get_user status=not_found telegram_id={telegram_id}")
                return None
        except SQLAlchemyError as e:
            log.exception(f"UsersRepoORM | action=get_user status=failed telegram_id={telegram_id} error={e}")
            raise

    async def get_users(self) -> list[UserDTO]:
        """
        Получает список всех пользователей.

        Returns:
            list[UserDTO]: Список пользователей.
        """
        log.debug("UsersRepoORM | action=get_users")
        stmt = select(User)

        try:
            result = await self.session.execute(stmt)
            orm_users_list = result.scalars().all()

            if orm_users_list:
                log.debug(f"UsersRepoORM | action=get_users status=found count={len(orm_users_list)}")
                return [UserDTO.model_validate(orm_user) for orm_user in orm_users_list]
            else:
                log.debug("UsersRepoORM | action=get_users status=not_found")
                return []
        except SQLAlchemyError as e:
            log.exception(f"UsersRepoORM | action=get_users status=failed error={e}")
            raise

    async def get_users_with_pagination(self, offset: int, limit: int) -> tuple[list[Any], int]:
        """
        Получает список пользователей с пагинацией.

        Args:
            offset: Смещение.
            limit: Лимит записей.

        Returns:
            tuple[list[Any], int]: Список пользователей и общее количество.
        """
        log.debug(f"UsersRepoORM | action=get_users_with_pagination offset={offset} limit={limit}")
        try:
            count_stmt = select(func.count(User.telegram_id))
            total_res = await self.session.execute(count_stmt)
            total = total_res.scalar_one()

            stmt = (
                select(User)
                .options(selectinload(User.characters))
                .order_by(User.telegram_id)
                .offset(offset)
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            orm_users_list = result.scalars().all()

            log.debug(
                f"UsersRepoORM | action=get_users_with_pagination status=success count={len(orm_users_list)} total={total}"
            )
            return list(orm_users_list), total
        except SQLAlchemyError as e:
            log.exception(f"UsersRepoORM | action=get_users_with_pagination status=failed error={e}")
            raise
