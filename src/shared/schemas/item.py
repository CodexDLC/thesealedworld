"""
Модуль содержит DTO (Data Transfer Objects) для работы с игровыми предметами.

Определяет базовые типы предметов, их редкость, а также детальные
структуры данных для различных категорий предметов (оружие, броня,
аксессуары, расходники, ресурсы) и их полиморфное представление.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from src.shared.enums.item_enums import ItemBonuses, ItemRarity, ItemType

# --- ВСПОМОГАТЕЛЬНЫЕ МОДЕЛИ ---


class ItemComponents(BaseModel):
    """
    Хранит информацию о том, из чего собран предмет.
    """

    base_id: str
    material_id: str
    essence_id: list[str] | None = None


class ItemDurability(BaseModel):
    """
    Информация о прочности предмета.
    """

    current: float
    max: float


# --- ОСНОВНЫЕ ДАННЫЕ ---


class ItemCoreData(BaseModel):
    """
    Базовые данные, которые лежат в JSON-поле `item_data` в БД.
    """

    name: str
    description: str
    base_price: int
    components: ItemComponents | None = None
    durability: ItemDurability | None = None
    narrative_tags: list[str] = Field(default_factory=list)

    # Встроенные бонусы (Implicit) - свойства материала/базы
    implicit_bonuses: ItemBonuses = Field(default_factory=dict)

    # Явные бонусы (Explicit) - заточка, суффиксы
    bonuses: ItemBonuses = Field(default_factory=dict)


# --- СПЕЦИФИЧНЫЕ ДАННЫЕ (RBC v3) ---


class WeaponData(ItemCoreData):
    """Данные оружия."""

    # Математика
    power: float  # Base Damage
    spread: float = 0.1  # Variance (0.1 = 10%)
    accuracy: float = 0.0  # Base Accuracy (может быть отрицательным)

    # Механика
    crit_chance: float = 0.0
    parry_chance: float = 0.0
    evasion_penalty: float = 0.0

    # Триггеры (ссылки на TriggerRegistry)
    triggers: list[str] = Field(default_factory=list)

    # Классификация
    grip: str = "1h"  # "1h", "2h"
    subtype: str  # "sword", "axe"
    related_skill: str | None = None  # "skill_swords"

    valid_slots: list[str]


class ArmorData(ItemCoreData):
    """Данные брони."""

    # Математика
    power: float  # Protection (Flat)

    # Механика
    block_chance: float = 0.0  # Только для щитов
    evasion_penalty: float = 0.0  # Штраф к шансу уворота
    dodge_cap_mod: float = 0.0  # Модификатор капа уворота (например, -0.25)

    # Триггеры (ссылки на TriggerRegistry)
    triggers: list[str] = Field(default_factory=list)

    # Классификация
    subtype: str  # "heavy", "light", "shield"
    related_skill: str | None = None  # "skill_heavy_armor"

    valid_slots: list[str]


class AccessoryData(ItemCoreData):
    """Данные аксессуаров."""

    # Триггеры (ссылки на TriggerRegistry)
    triggers: list[str] = Field(default_factory=list)

    valid_slots: list[str]


class ConsumableData(ItemCoreData):
    """Данные расходников."""

    restore_hp: int = 0
    restore_energy: int = 0
    effects: list[str] = Field(default_factory=list)
    cooldown_rounds: int = 0
    is_quick_slot_compatible: bool = False


class ResourceData(ItemCoreData):
    """Данные ресурсов."""

    pass


# --- DTO ДЛЯ ИНВЕНТАРЯ ---


class BaseInventoryItemDTO(BaseModel):
    """Основа, маппится на колонки таблицы inventory_items."""

    inventory_id: int
    character_id: int
    location: str
    subtype: str
    rarity: ItemRarity
    quantity: int = 1
    equipped_slot: str | None = None
    quick_slot_position: str | None = None
    model_config = ConfigDict(from_attributes=True)


class WeaponItemDTO(BaseInventoryItemDTO):
    """DTO оружия в инвентаре."""

    item_type: Literal[ItemType.WEAPON]
    data: WeaponData


class ArmorItemDTO(BaseInventoryItemDTO):
    """DTO брони в инвентаре."""

    item_type: Literal[ItemType.ARMOR]
    data: ArmorData


class AccessoryItemDTO(BaseInventoryItemDTO):
    """DTO аксессуара в инвентаре."""

    item_type: Literal[ItemType.ACCESSORY]
    data: AccessoryData


class ConsumableItemDTO(BaseInventoryItemDTO):
    """DTO расходника в инвентаре."""

    item_type: Literal[ItemType.CONSUMABLE]
    data: ConsumableData


class ResourceItemDTO(BaseInventoryItemDTO):
    """DTO ресурса в инвентаре."""

    item_type: Literal[ItemType.RESOURCE, ItemType.CURRENCY]
    data: ResourceData


# Полиморфный Union
InventoryItemDTO = Annotated[
    WeaponItemDTO | ArmorItemDTO | AccessoryItemDTO | ConsumableItemDTO | ResourceItemDTO,
    Field(discriminator="item_type"),
]

InventoryItemTypeAdapter: TypeAdapter[InventoryItemDTO] = TypeAdapter(InventoryItemDTO)
