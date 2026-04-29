from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from src.shared.enums.item_enums import ItemBonuses, ItemRarity, ItemType


class ItemComponents(BaseModel):
    base_id: str
    material_id: str
    essence_id: list[str] | None = None


class ItemDurability(BaseModel):
    current: float
    max: float


class ItemCoreData(BaseModel):
    name: str
    description: str
    base_price: int
    components: ItemComponents | None = None
    durability: ItemDurability | None = None
    narrative_tags: list[str] = Field(default_factory=list)
    implicit_bonuses: ItemBonuses = Field(default_factory=dict)
    bonuses: ItemBonuses = Field(default_factory=dict)


class WeaponData(ItemCoreData):
    power: float
    spread: float = 0.1
    accuracy: float = 0.0
    crit_chance: float = 0.0
    parry_chance: float = 0.0
    evasion_penalty: float = 0.0
    triggers: list[str] = Field(default_factory=list)
    grip: str = "1h"
    subtype: str
    related_skill: str | None = None
    valid_slots: list[str]


class ArmorData(ItemCoreData):
    power: float
    block_chance: float = 0.0
    evasion_penalty: float = 0.0
    dodge_cap_mod: float = 0.0
    triggers: list[str] = Field(default_factory=list)
    subtype: str
    related_skill: str | None = None
    valid_slots: list[str]


class AccessoryData(ItemCoreData):
    triggers: list[str] = Field(default_factory=list)
    valid_slots: list[str]


class ConsumableData(ItemCoreData):
    restore_hp: int = 0
    restore_energy: int = 0
    effects: list[str] = Field(default_factory=list)
    cooldown_rounds: int = 0
    is_quick_slot_compatible: bool = False


class ResourceData(ItemCoreData):
    pass


class BaseInventoryItemDTO(BaseModel):
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
    item_type: Literal[ItemType.WEAPON]
    data: WeaponData


class ArmorItemDTO(BaseInventoryItemDTO):
    item_type: Literal[ItemType.ARMOR]
    data: ArmorData


class AccessoryItemDTO(BaseInventoryItemDTO):
    item_type: Literal[ItemType.ACCESSORY]
    data: AccessoryData


class ConsumableItemDTO(BaseInventoryItemDTO):
    item_type: Literal[ItemType.CONSUMABLE]
    data: ConsumableData


class ResourceItemDTO(BaseInventoryItemDTO):
    item_type: Literal[ItemType.RESOURCE, ItemType.CURRENCY]
    data: ResourceData


InventoryItemDTO = Annotated[
    WeaponItemDTO | ArmorItemDTO | AccessoryItemDTO | ConsumableItemDTO | ResourceItemDTO,
    Field(discriminator="item_type"),
]

InventoryItemTypeAdapter: TypeAdapter[InventoryItemDTO] = TypeAdapter(InventoryItemDTO)
