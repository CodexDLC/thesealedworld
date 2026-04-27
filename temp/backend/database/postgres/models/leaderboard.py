from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database.postgres.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from .character import Character


class Leaderboard(Base, TimestampMixin):
    """
    ORM-модель для таблицы `leaderboards`.

    Хранит агрегированную статистику персонажей для матчмейкинга
    и отображения в рейтинговых таблицах.
    """

    __tablename__ = "leaderboards"

    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        primary_key=True,
        comment="Идентификатор персонажа (первичный и внешний ключ).",
    )

    gear_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        index=True,
        comment="Общий показатель силы персонажа (Gear Score), используется для матчмейкинга.",
    )
    total_xp: Mapped[int] = mapped_column(
        BigInteger, default=0, index=True, comment="Общее количество накопленного опыта персонажем."
    )
    pvp_rating: Mapped[int] = mapped_column(
        Integer, default=1000, index=True, comment="Рейтинг PvP персонажа (например, ELO/MMR)."
    )

    character: Mapped[Character] = relationship(backref="leaderboard")

    def __repr__(self) -> str:
        return f"<Leaderboard(char_id={self.character_id}, gs={self.gear_score})>"
