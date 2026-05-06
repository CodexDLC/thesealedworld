from enum import StrEnum


class EquippedSlot(StrEnum):
    HEAD_ARMOR = "head_armor"
    CHEST_ARMOR = "chest_armor"
    ARMS_ARMOR = "arms_armor"
    LEGS_ARMOR = "legs_armor"
    CHEST_GARMENT = "chest_garment"
    LEGS_GARMENT = "legs_garment"
    OUTER_GARMENT = "outer_garment"
    GLOVES_GARMENT = "gloves_garment"
    FEETWEAR = "feetwear"
    MAIN_HAND = "main_hand"
    OFF_HAND = "off_hand"
    TWO_HAND = "two_hand"
    AMULET = "amulet"
    EARRING = "earring"
    RING_1 = "ring_1"
    RING_2 = "ring_2"
    BELT_ACCESSORY = "belt_accessory"


class QuickSlot(StrEnum):
    BELT_SLOT_1 = "belt_slot_1"
    BELT_SLOT_2 = "belt_slot_2"
    BELT_SLOT_3 = "belt_slot_3"
    BELT_SLOT_4 = "belt_slot_4"
    BELT_SLOT_5 = "belt_slot_5"
    BELT_SLOT_6 = "belt_slot_6"
    BELT_SLOT_7 = "belt_slot_7"
    BELT_SLOT_8 = "belt_slot_8"


class ItemType(StrEnum):
    WEAPON = "weapon"
    ARMOR = "armor"
    ACCESSORY = "accessory"
    CONSUMABLE = "consumable"
    CONTAINER = "container"
    RESOURCE = "resource"
    CURRENCY = "currency"
    GARMENT = "garment"
    MATERIAL = "material"
    QUEST = "quest"


class ItemRarity(StrEnum):
    COMMON = "shared"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"
    EXOTIC = "exotic"
    ABSOLUTE = "absolute"


ItemBonuses = dict[str, float | int]
