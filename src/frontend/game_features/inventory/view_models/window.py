from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

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
    slot_id: str = ""
    slot_index: int
    is_empty: bool = True
    item_id: str | None = None
    label: str = "EMPTY"
    enabled: bool = False
    reason: str = "belt_contract_pending"


class InventoryTabVM(BaseModel):
    tab_id: str
    label: str
    icon: str
    is_active: bool = False


class InventoryStatsVM(BaseModel):
    slots_total: int = 50
    slots_used: int = 0


class InventoryRowVM(BaseModel):
    row_id: str
    icon: str
    name: str
    item_type: str
    weight: str
    quantity: str
    rarity: str
    rarity_tier: int = 0
    rarity_label: str = "Без грейда"
    equip_target: str | None = None
    grid_w: int = 2
    grid_h: int = 1
    is_equipped: bool = False
    comparison: list[str] = Field(default_factory=list)


class InventoryCardVM(BaseModel):
    row_id: str
    icon: str
    name: str
    item_type: str
    weight: str
    quantity: str
    rarity: str
    rarity_tier: int
    rarity_label: str
    equip_target: str | None = None
    grid_w: int
    grid_h: int
    style: str
    card_class: str
    is_equipped: bool = False
    details: list[str] = Field(default_factory=list)
    comparison: list[str] = Field(default_factory=list)


def build_inventory_card_vm(row: InventoryRowVM) -> InventoryCardVM:
    grid_w, grid_h = inventory_card_dimensions(row.item_type, row.grid_w, row.grid_h)
    details = [
        f"Тип: {row.item_type}",
        f"Вес: {row.weight}",
        f"Кол-во: {row.quantity}",
        f"Грейд: {row.rarity}",
        *row.comparison,
    ]
    return InventoryCardVM(
        row_id=row.row_id,
        icon=row.icon,
        name=row.name,
        item_type=row.item_type,
        weight=row.weight,
        quantity=row.quantity,
        rarity=row.rarity,
        rarity_tier=max(0, min(7, row.rarity_tier)),
        rarity_label=row.rarity_label,
        equip_target=row.equip_target,
        grid_w=grid_w,
        grid_h=grid_h,
        style=f"--item-w: {grid_w}; --item-h: {grid_h};",
        card_class=inventory_card_class(row.item_type, grid_w, grid_h),
        is_equipped=row.is_equipped,
        details=details,
        comparison=row.comparison,
    )


def inventory_card_dimensions(item_type: str, grid_w: int | None = None, grid_h: int | None = None) -> tuple[int, int]:
    width = int(grid_w or 0)
    height = int(grid_h or 0)
    if width < 1:
        width = 1 if item_type in {"resource", "currency", "material", "consumable", "quest"} else 2
    if height < 1:
        height = 1 if item_type in {"resource", "currency", "material", "consumable", "quest"} else 2
    return max(1, min(8, width)), max(1, min(4, height))


def inventory_card_class(item_type: str, grid_w: int, grid_h: int) -> str:
    normalized_type = item_type.lower().replace("_", "-")
    shape = "square" if grid_w == grid_h else "wide" if grid_w > grid_h else "tall"
    footprint = "compact" if grid_w * grid_h <= 2 else "large" if grid_w * grid_h >= 8 else "medium"
    return " ".join(
        [
            f"inventory-card--{normalized_type}",
            f"inventory-card--{shape}",
            f"inventory-card--{footprint}",
            f"inventory-card--{grid_w}x{grid_h}",
        ]
    )


class InventoryWindowVM(BaseModel):
    avatar_url: str
    avatar_name: str
    body_zones: list[InventoryBodyZoneVM]
    weapon_slots: list[InventorySlotVM]
    accessory_rows: list[InventoryAccessoryRowVM]
    quick_slots: list[InventoryQuickSlotVM]
    tabs: list[InventoryTabVM]
    visible_rows: list[InventoryRowVM]
    visible_cards: list[InventoryCardVM] = Field(default_factory=list)
    stats: InventoryStatsVM = Field(default_factory=InventoryStatsVM)
    rows_visible_count: int = 10
    search_placeholder: str = "Поиск"
    contract_state: str = "FRONTEND_CONTRACT_PENDING"

    @model_validator(mode="after")
    def populate_inventory_cards(self) -> InventoryWindowVM:
        if not self.visible_cards and self.visible_rows:
            self.visible_cards = [build_inventory_card_vm(row) for row in self.visible_rows]
        return self


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
                label="Голова",
                primary_slot=_slot("head_armor", "Шлем", "armor"),
                position="head",
            ),
            InventoryBodyZoneVM(
                zone_id="outer",
                label="Плащ",
                primary_slot=_slot("outer_garment", "Плащ", "garment"),
                position="outer",
            ),
            InventoryBodyZoneVM(
                zone_id="chest",
                label="Корпус",
                primary_slot=_slot("chest_armor", "Броня", "armor"),
                secondary_slot=_slot("chest_garment", "Одежда", "garment"),
                position="chest",
            ),
            InventoryBodyZoneVM(
                zone_id="arms",
                label="Руки",
                primary_slot=_slot("arms_armor", "Наручи", "armor"),
                secondary_slot=_slot("gloves_garment", "Перчатки", "garment"),
                position="arms",
            ),
            InventoryBodyZoneVM(
                zone_id="legs",
                label="Ноги",
                primary_slot=_slot("legs_armor", "Поножи", "armor"),
                secondary_slot=_slot("legs_garment", "Штаны", "garment"),
                position="legs",
            ),
            InventoryBodyZoneVM(
                zone_id="feet",
                label="Обувь",
                primary_slot=_slot("feetwear", "Обувь", "equipment"),
                position="feet",
            ),
        ],
        weapon_slots=[
            _slot("main_hand", "Основная", "equipment"),
            _slot("off_hand", "Вторая", "equipment"),
        ],
        accessory_rows=[
            InventoryAccessoryRowVM(row_id="amulet", label="Амулет", slots=[_slot("amulet", "Амулет", "accessory")]),
            InventoryAccessoryRowVM(
                row_id="earrings",
                label="Серьги",
                slots=[_slot("earring", "Серьги", "accessory")],
            ),
            InventoryAccessoryRowVM(
                row_id="rings",
                label="Кольца",
                slots=[_slot("ring_1", "Кольцо 1", "accessory"), _slot("ring_2", "Кольцо 2", "accessory")],
                is_wide=False,
            ),
            InventoryAccessoryRowVM(
                row_id="belt",
                label="Пояс",
                slots=[_slot("belt_accessory", "Пояс", "accessory")],
            ),
        ],
        quick_slots=[InventoryQuickSlotVM(slot_id=f"belt_slot_{index}", slot_index=index) for index in range(1, 9)],
        tabs=[
            InventoryTabVM(tab_id="items", label="Предметы", icon="I", is_active=True),
            InventoryTabVM(tab_id="resources", label="Ресурсы", icon="R"),
            InventoryTabVM(tab_id="quest", label="Квест", icon="Q"),
        ],
        visible_rows=[],
        visible_cards=[],
        stats=InventoryStatsVM(slots_total=50, slots_used=0),
    )


def _slot(slot_id: str, label: str, layer: SlotLayer) -> InventorySlotVM:
    return InventorySlotVM(slot_id=slot_id, label=label, layer=layer, compare_slot_id=slot_id)
