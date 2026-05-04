from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database.postgres.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from .character import Character


class User(Base, TimestampMixin):
    """
    ORM-модель для таблицы `users`.

    Представляет пользователя Telegram в системе, храня его основные данные
    и связывая с созданными им персонажами.
    """

    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, comment="Уникальный идентификатор пользователя в Telegram."
    )
    first_name: Mapped[str] = mapped_column(String(64), comment="Имя пользователя.")
    username: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="Никнейм пользователя в Telegram (может отсутствовать)."
    )
    last_name: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="Фамилия пользователя (может отсутствовать)."
    )
    language_code: Mapped[str] = mapped_column(
        String(10), default="ru", nullable=False, comment="Языковой код, полученный от Telegram."
    )
    is_premium: Mapped[bool] = mapped_column(
        default=False, nullable=False, comment="Флаг, указывающий, является ли пользователь Telegram Premium."
    )

    characters: Mapped[list[Character]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """
        Возвращает строковое представление объекта User.
        """
        return f"<User(telegram_id={self.telegram_id}, first_name='{self.first_name}', username='{self.username}')>"
