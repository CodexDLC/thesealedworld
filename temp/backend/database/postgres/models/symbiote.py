from __future__ import annotations

from typing import TYPE_CHECKING

from archive.telegram_bot import DEFAULT_ACTOR_NAME
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database.postgres.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from .character import Character


class CharacterSymbiote(Base, TimestampMixin):
    """
    ORM-модель для таблицы `character_symbiotes`.

    Представляет Симбиота — сущность-спутник и источник Дара (Магии)
    для персонажа. Его развитие синхронизировано с рангом Дара.
    """

    __tablename__ = "character_symbiotes"

    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        primary_key=True,
        comment="Идентификатор персонажа, которому принадлежит Симбиот (первичный и внешний ключ).",
    )

    symbiote_name: Mapped[str] = mapped_column(
        String(50), default=DEFAULT_ACTOR_NAME, nullable=False, comment="Имя Симбиота (помощника)."
    )
    gift_id: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default=None, comment="Ключ Дара (магической школы), которым владеет Симбиот."
    )
    gift_xp: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="Опыт Дара, накопленный Симбиотом."
    )
    gift_rank: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, comment="Ранг Дара (фактический 'уровень' Симбиота)."
    )

    elements_resonance: Mapped[dict] = mapped_column(
        JSONB,
        default=lambda: {"fire": 0, "water": 0, "earth": 0, "air": 0, "dark": 0, "arcane": 0, "light": 0, "nature": 0},
        nullable=False,
        comment="Накопленный резонанс с элементами (fire, water, earth, air, dark, arcane, light, nature).",
    )

    character: Mapped[Character] = relationship(back_populates="symbiote")

    def __repr__(self) -> str:
        return (
            f"<Symbiote(char_id={self.character_id}, "
            f"name='{self.symbiote_name}', "
            f"gift='{self.gift_id}', "
            f"rank={self.gift_rank})>"
        )
