from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

DEFAULT_INVENTORY_AVATAR_URL = "/static/images/avatars/silhouette_m.png"

SlotLayer = Literal["armor", "garment", "equipment", "accessory", "quick"]


class InventorySlotVM(BaseModel):
    slot_id: str
    label: str
    layer: SlotLayer
    item_id: str | None = None
    item_name: str = "EMPTY"
    item_type: str = "NO_DATA"
    rarity: str = "none"
    is_empty: bool = True
    compare_slot_id: str | None = None


class InventoryBodyZoneVM(BaseModel):
    zone_id: str
    label: str
    primary_slot: InventorySlotVM
    secondary_slot: InventorySlotVM | None = None
    position: str


class InventoryAccessoryRowVM(BaseModel):
    row_id: str
    label: str
    slots: list[InventorySlotVM]
    is_wide: bool = True


class InventoryQuickSlotVM(BaseModel):
    slot_index: int
    is_empty: bool = True
    item_id: str | None = None
    label: str = "EMPTY"
    reason: str = "belt_contract_pending"


class InventoryTabVM(BaseModel):
    tab_id: str
    label: str
    icon: str
    is_active: bool = False


class InventoryRowVM(BaseModel):
    row_id: str
    icon: str
    name: str
    item_type: str
    weight: str
    quantity: str
    rarity: str
    equip_target: str | None = None
    comparison: list[str] = Field(default_factory=list)


class InventoryWindowVM(BaseModel):
    avatar_url: str
    avatar_name: str
    body_zones: list[InventoryBodyZoneVM]
    weapon_slots: list[InventorySlotVM]
    accessory_rows: list[InventoryAccessoryRowVM]
    quick_slots: list[InventoryQuickSlotVM]
    tabs: list[InventoryTabVM]
    visible_rows: list[InventoryRowVM]
    rows_visible_count: int = 10
    search_placeholder: str = "Search"
    contract_state: str = "FRONTEND_CONTRACT_PENDING"


def build_inventory_window_vm(status_seed: dict[str, Any] | None = None) -> InventoryWindowVM:
    status_seed = status_seed or {}
    avatar_url = str(status_seed.get("avatar_url") or DEFAULT_INVENTORY_AVATAR_URL)
    avatar_name = str(status_seed.get("name") or "NO_DATA")

    return InventoryWindowVM(
        avatar_url=avatar_url,
        avatar_name=avatar_name,
        body_zones=[
            InventoryBodyZoneVM(
                zone_id="head",
                label="Head",
                primary_slot=_slot("head_armor", "Helmet", "armor"),
                position="head",
            ),
            InventoryBodyZoneVM(
                zone_id="outer",
                label="Cloak",
                primary_slot=_slot("outer_garment", "Cloak", "garment"),
                position="outer",
            ),
            InventoryBodyZoneVM(
                zone_id="chest",
                label="Torso",
                primary_slot=_slot("chest_armor", "Armor", "armor"),
                secondary_slot=_slot("chest_garment", "Clothing", "garment"),
                position="chest",
            ),
            InventoryBodyZoneVM(
                zone_id="arms",
                label="Arms",
                primary_slot=_slot("arms_armor", "Bracers", "armor"),
                secondary_slot=_slot("gloves_garment", "Gloves", "garment"),
                position="arms",
            ),
            InventoryBodyZoneVM(
                zone_id="legs",
                label="Legs",
                primary_slot=_slot("legs_armor", "Leg Armor", "armor"),
                secondary_slot=_slot("legs_garment", "Pants", "garment"),
                position="legs",
            ),
            InventoryBodyZoneVM(
                zone_id="feet",
                label="Footwear",
                primary_slot=_slot("feetwear", "Boots", "equipment"),
                position="feet",
            ),
        ],
        weapon_slots=[
            _slot("main_hand", "Main Hand", "equipment"),
            _slot("off_hand", "Off Hand", "equipment"),
        ],
        accessory_rows=[
            InventoryAccessoryRowVM(row_id="amulet", label="Amulet", slots=[_slot("amulet", "Amulet", "accessory")]),
            InventoryAccessoryRowVM(
                row_id="earrings",
                label="Earrings",
                slots=[_slot("earring", "Earrings", "accessory")],
            ),
            InventoryAccessoryRowVM(
                row_id="rings",
                label="Rings",
                slots=[_slot("ring_1", "Ring 1", "accessory"), _slot("ring_2", "Ring 2", "accessory")],
                is_wide=False,
            ),
            InventoryAccessoryRowVM(
                row_id="belt",
                label="Belt",
                slots=[_slot("belt_accessory", "Belt", "accessory")],
            ),
        ],
        quick_slots=[InventoryQuickSlotVM(slot_index=index) for index in range(1, 9)],
        tabs=[
            InventoryTabVM(tab_id="equipped", label="Equipped", icon="E", is_active=True),
            InventoryTabVM(tab_id="items", label="Items", icon="I"),
            InventoryTabVM(tab_id="resources", label="Resources", icon="R"),
            InventoryTabVM(tab_id="quest", label="Quest", icon="Q"),
        ],
        visible_rows=[],
    )


def _slot(slot_id: str, label: str, layer: SlotLayer) -> InventorySlotVM:
    return InventorySlotVM(slot_id=slot_id, label=label, layer=layer, compare_slot_id=slot_id)
