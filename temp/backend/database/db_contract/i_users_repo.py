from abc import ABC, abstractmethod
from typing import Any

from src.shared.schemas.user import UserDTO, UserUpsertDTO


class IUserRepo(ABC):
    """
    Абстрактный базовый класс (интерфейс) для репозитория пользователей.

    Определяет контракт, которому должны следовать все конкретные реализации
    репозиториев пользователей, независимо от используемой базы данных.
    """

    @abstractmethod
    async def upsert_user(self, user_data: UserUpsertDTO) -> UserDTO:
        """
        Создает нового пользователя или обновляет данные существующего.

        Реализация этого метода должна обеспечивать атомарность операции:
        если пользователь с указанным `telegram_id` существует, его данные
        (first_name, username и т.д.) обновляются. Если не существует -
        создается новая запись.

        Args:
            user_data: DTO с данными для создания или обновления пользователя.

        Returns:
            UserDTO с актуальными данными пользователя (включая created_at, updated_at).
        """
        pass

    @abstractmethod
    async def get_user(self, telegram_id: int) -> UserDTO | None:
        """
        Находит и возвращает одного пользователя по его `telegram_id`.

        Args:
            telegram_id: Уникальный идентификатор пользователя в Telegram.

        Returns:
            DTO `UserDTO` с полными данными пользователя, если он найден,
            в противном случае - None.
        """
        pass

    @abstractmethod
    async def get_users(self) -> list[UserDTO]:
        """
        Возвращает список всех пользователей в системе.

        Этот метод может использоваться для административных задач,
        рассылок или отладки.

        Returns:
            Список DTO `UserDTO` всех пользователей.
            Если пользователей нет, возвращает пустой список.
        """
        pass

    @abstractmethod
    async def get_users_with_pagination(self, offset: int, limit: int) -> tuple[list[Any], int]:
        """
        Возвращает страницу пользователей и общее их количество.
        Возвращает ORM-объекты (или расширенные DTO), чтобы был доступ к characters.
        """
        pass
