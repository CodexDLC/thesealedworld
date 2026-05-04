# --- ENUMS ---
from enum import StrEnum


class EquippedSlot(StrEnum):
    """
    Слоты экипировки персонажа.
    """

    HEAD_ARMOR = "head_armor"
    CHEST_ARMOR = "chest_armor"
    ARMS_ARMOR = "arms_armor"
    LEGS_ARMOR = "legs_armor"
    FEET_ARMOR = "feet_armor"
    CHEST_GARMENT = "chest_garment"
    LEGS_GARMENT = "legs_garment"
    OUTER_GARMENT = "outer_garment"
    GLOVES_GARMENT = "gloves_garment"
    MAIN_HAND = "main_hand"
    OFF_HAND = "off_hand"
    TWO_HAND = "two_hand"
    AMULET = "amulet"
    EARRING = "earring"
    RING_1 = "ring_1"
    RING_2 = "ring_2"
    BELT_ACCESSORY = "belt_accessory"


class QuickSlot(StrEnum):
    """
    Слоты быстрого доступа (для расходников).
    """

    QUICK_SLOT_1 = "quick_slot_1"
    QUICK_SLOT_2 = "quick_slot_2"
    QUICK_SLOT_3 = "quick_slot_3"
    QUICK_SLOT_4 = "quick_slot_4"


class ItemType(StrEnum):
    """
    Основные типы предметов.
    """

    WEAPON = "weapon"
    ARMOR = "armor"
    ACCESSORY = "accessory"
    CONSUMABLE = "consumable"
    CONTAINER = "container"
    RESOURCE = "resource"
    CURRENCY = "currency"


class ItemRarity(StrEnum):
    """
    Редкость предметов.
    """

    COMMON = "shared"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"
    EXOTIC = "exotic"
    ABSOLUTE = "absolute"


ItemBonuses = dict[str, float | int]
