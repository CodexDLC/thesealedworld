from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database.postgres.models.base import Base

if TYPE_CHECKING:
    from .character import Character


class InventoryItem(Base):
    """
    ORM-модель для таблицы `inventory_items`.

    Представляет уникальный предмет в инвентаре персонажа,
    храня его основные свойства и детальные данные в JSON-поле.
    """

    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="Уникальный идентификатор предмета в инвентаре."
    )
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        nullable=False,
        comment="Идентификатор персонажа, которому принадлежит предмет.",
    )
    item_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Тип предмета (например, 'weapon', 'armor', 'accessory')."
    )
    subtype: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="Подтип предмета (например, 'sword', 'chest_plate', 'ring')."
    )
    rarity: Mapped[str] = mapped_column(
        String(20), default="shared", comment="Редкость предмета (например, 'shared', 'rare', 'epic')."
    )
    location: Mapped[str] = mapped_column(
        String(20),
        default="inventory",
        comment="Местонахождение предмета ('inventory', 'equipped', 'auction', 'bank').",
    )
    quantity: Mapped[int] = mapped_column(
        Integer, default=1, comment="Количество предметов (для стакающихся предметов)."
    )
    item_data: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        comment="JSON-поле, содержащее детальные данные предмета (название, описание, статы, бонусы).",
    )

    equipped_slot: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Слот экипировки (head_armor, ring_1, etc.)."
    )

    quick_slot_position: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Позиция в быстром доступе (quick_slot_1, etc.)."
    )

    character: Mapped[Character] = relationship(back_populates="inventory")

    def __repr__(self):
        return f"<Item {self.id} ({self.rarity} {self.subtype})>"


class ResourceWallet(Base):
    """
    Кошелек Ресурсов (3 Столпа Экономики).
    Все поля — JSON словари { "item_id": amount }.
    """

    __tablename__ = "resource_wallets"

    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"), primary_key=True
    )

    # 1. ВАЛЮТА (Катализаторы)
    # Пыль (dust), Осколки (shards), Ядра (cores).
    # Выделено, чтобы легко проверять баланс и делать транзакции.
    currency: Mapped[dict] = mapped_column(JSON, default=dict)

    # 2. СЫРЬЕ (Tier 0 - Gathered)
    # Всё, что добывается в мире: Руда, Шкуры, Бревна, Травы, Эссенции.
    # Пример: { "res_iron_ore": 10, "res_wolf_pelt": 5 }
    resources: Mapped[dict] = mapped_column(JSON, default=dict)

    # 3. КОМПОНЕНТЫ (Tier 1+ - Crafted/Refined)
    # Всё, что прошло обработку: Слитки, Кожа, Ткань, Лезвия, Рукояти.
    # Пример: { "mat_iron_ingot": 2, "part_blade_iron": 1 }
    components: Mapped[dict] = mapped_column(JSON, default=dict)

    character: Mapped[Character] = relationship("Character", back_populates="wallet")

    def __repr__(self):
        return f"<Wallet char_id={self.character_id}>"
