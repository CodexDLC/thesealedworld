from typing import Any, Literal

from pydantic import BaseModel, Field

from src.shared.enums.inventory_enums import InventorySection
from src.shared.enums.item_enums import EquippedSlot, QuickSlot
from src.shared.schemas.item import InventoryItemDTO

# --- SESSION DTOs (Redis Storage) ---


class WalletDTO(BaseModel):
    """
    Кошелек игрока.
    Хранит валюту и ресурсы.
    """

    currency: dict[str, int] = Field(default_factory=dict)  # gold, dust, tokens
    resources: dict[str, int] = Field(default_factory=dict)  # wood, iron (если храним тут)
    components: dict[str, int] = Field(default_factory=dict)  # gear, essence


class InventoryStatsDTO(BaseModel):
    """
    Кэшированные статы инвентаря.
    """

    max_weight: float = 100.0
    current_weight: float = 0.0
    slots_total: int = 50
    slots_used: int = 0


class InventorySessionDTO(BaseModel):
    """
    Полное состояние инвентаря (хранится в Redis).
    """

    char_id: int

    # Все предметы в инвентаре (Сумка + Надетые)
    # Key: inventory_id (int) -> Item
    items: dict[int, InventoryItemDTO] = Field(default_factory=dict)

    # Ссылки на надетые предметы
    # Key: slot_name (str) -> inventory_id (int)
    # Мы храним только ID, чтобы не дублировать данные. Сами предметы лежат в items.
    equipped: dict[str, int] = Field(default_factory=dict)

    wallet: WalletDTO = Field(default_factory=WalletDTO)
    stats: InventoryStatsDTO = Field(default_factory=InventoryStatsDTO)

    # Флаг изменений (для Write-Back)
    is_dirty: bool = False
    updated_at: float = 0.0


# --- Runtime inventory session (Redis) ---


class InventoryLayoutDTO(BaseModel):
    equipment: dict[str, str | None] = Field(default_factory=dict)
    belt: dict[str, str | None] = Field(default_factory=dict)
    backpack: list[str] = Field(default_factory=list)


class InventoryRuntimeItemDTO(BaseModel):
    item_id: str
    base_id: str
    item_type: str
    slot: str | None = None
    valid_slots: list[str] = Field(default_factory=list)
    placement: str = "backpack"
    name: str
    description: str = ""
    rarity: str = "shared"
    rarity_tier: int = 0
    quantity: int = 1
    sync_state: str = "secured"
    is_unsecured: bool = False
    mechanics: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class InventoryRuntimeSessionDTO(BaseModel):
    char_id: int
    layout: InventoryLayoutDTO = Field(default_factory=InventoryLayoutDTO)
    by_id: dict[str, InventoryRuntimeItemDTO] = Field(default_factory=dict)
    wallet: WalletDTO = Field(default_factory=WalletDTO)
    stats: InventoryStatsDTO = Field(default_factory=InventoryStatsDTO)
    risk_run_id: str | None = None
    is_dirty: bool = False
    dirty: dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    updated_at: float = 0.0


class ActiveCharacterItemsProjectionDTO(BaseModel):
    layout: InventoryLayoutDTO = Field(default_factory=InventoryLayoutDTO)
    by_id: dict[str, InventoryRuntimeItemDTO] = Field(default_factory=dict)


# --- VIEW DTOs (Client Response) ---


class EnrichedCurrencyDTO(BaseModel):
    """
    Обогащенные данные о валюте/ресурсе для отображения.
    """

    id: str
    name: str
    amount: int
    icon: str | None = None  # Клиент может добавить иконку по ID


class WalletViewDTO(BaseModel):
    """
    Обогащенные данные кошелька для UI.
    """

    currency: list[EnrichedCurrencyDTO]
    resources: list[EnrichedCurrencyDTO]
    components: list[EnrichedCurrencyDTO]


class ButtonDTO(BaseModel):
    """
    Универсальная кнопка для UI.
    """

    text: str
    action: str  # callback prefix or action name
    payload: dict[str, Any] | None = None
    is_active: bool = True
    style: str = "primary"  # primary, secondary, danger


class PaginationDTO(BaseModel):
    page: int
    total_pages: int
    has_next: bool
    has_prev: bool


# Contexts for different screens


class BagContextDTO(BaseModel):
    """
    Данные для отрисовки сумки.
    """

    items: list[InventoryItemDTO]
    pagination: PaginationDTO
    active_section: InventorySection
    active_category: str | None = None
    back_target: str | None = None


class DollContextDTO(BaseModel):
    """
    Данные для отрисовки куклы персонажа.
    """

    # Slot -> Item (полный объект для отображения)
    equipped_items: dict[str, InventoryItemDTO]
    stats: dict[str, Any]  # Сводка статов (Atk, Def)
    wallet: WalletViewDTO  # Используем обогащенный DTO


class DetailsContextDTO(BaseModel):
    """
    Данные для отрисовки карточки предмета.
    """

    item: InventoryItemDTO
    comparison_item: InventoryItemDTO | None = None  # Предмет, с которым сравниваем
    actions: list[ButtonDTO]  # Доступные действия (Надеть, Снять, Выбросить)
    back_target: str


# Payload Union


class InventoryUIPayloadDTO(BaseModel):
    """
    Единый пейлоад для UI Инвентаря.
    Вкладывается в CoreCompositeResponseDTO.payload.
    """

    screen: str  # main, bag, details
    title: str

    # Один из контекстов
    context: BagContextDTO | DollContextDTO | DetailsContextDTO

    # Общие кнопки (например, нижнее меню навигации)
    navigation_buttons: list[ButtonDTO] = Field(default_factory=list)


# --- Window/action API DTOs ---


InventorySlotLayer = Literal["armor", "garment", "equipment", "accessory", "quick"]
InventoryLineTone = Literal["positive", "negative", "neutral"]
InventoryActionStyle = Literal["primary", "secondary", "danger"]
InventoryTabId = Literal["items", "resources", "quest"]


class InventoryDetailLineDTO(BaseModel):
    label: str
    value: str
    tone: InventoryLineTone = "neutral"
    delta: float | None = None


class InventoryAffixLineDTO(BaseModel):
    affix_id: str
    label: str
    value: str
    tier: int = Field(default=0, ge=0, le=7)
    source: str | None = None
    tone: InventoryLineTone = "neutral"


class InventoryRequirementDTO(BaseModel):
    label: str
    value: str
    met: bool = False
    current: str | None = None


class InventoryEffectTagDTO(BaseModel):
    label: str
    tone: InventoryLineTone = "neutral"


class InventoryMetaFieldDTO(BaseModel):
    label: str
    value: str


class InventoryItemActionDTO(BaseModel):
    action: Literal["equip", "unequip", "move_to_belt", "remove_from_belt", "use", "drop"]
    label: str
    enabled: bool = True
    reason: str | None = None
    slot_id: str | None = None
    style: InventoryActionStyle = "secondary"


class InventoryItemDetailsDTO(BaseModel):
    item_id: str
    name: str
    item_type: str
    item_type_label: str = "Предмет"
    rarity: str = "shared"
    rarity_tier: int = Field(default=0, ge=0, le=7)
    rarity_label: str = "Без грейда"
    description: str = ""
    flavor: str | None = None
    details: list[InventoryDetailLineDTO] = Field(default_factory=list)
    affixes: list[InventoryAffixLineDTO] = Field(default_factory=list)
    comparison: list[InventoryDetailLineDTO] = Field(default_factory=list)
    effects: list[InventoryEffectTagDTO] = Field(default_factory=list)
    tags: list[InventoryEffectTagDTO] = Field(default_factory=list)
    requirements: list[InventoryRequirementDTO] = Field(default_factory=list)
    meta: list[InventoryMetaFieldDTO] = Field(default_factory=list)
    actions: list[InventoryItemActionDTO] = Field(default_factory=list)


class InventoryWindowSlotDTO(BaseModel):
    slot_id: str
    label: str
    layer: InventorySlotLayer
    item: InventoryRuntimeItemDTO | None = None
    details: InventoryItemDetailsDTO | None = None
    accepted_slots: list[str] = Field(default_factory=list)


class InventoryBodyZoneDTO(BaseModel):
    zone_id: str
    label: str
    primary_slot: InventoryWindowSlotDTO
    secondary_slot: InventoryWindowSlotDTO | None = None
    position: str


class InventoryAccessoryRowDTO(BaseModel):
    row_id: str
    label: str
    slots: list[InventoryWindowSlotDTO]
    is_wide: bool = True


class InventoryQuickSlotDTO(BaseModel):
    slot_id: str
    slot_index: int
    item: InventoryRuntimeItemDTO | None = None
    details: InventoryItemDetailsDTO | None = None
    enabled: bool = False
    reason: str = "empty"


class InventoryTabDTO(BaseModel):
    tab_id: InventoryTabId
    label: str
    icon: str
    is_active: bool = False


class InventoryComparisonLineDTO(BaseModel):
    label: str
    value: str
    delta: float | None = None
    tone: InventoryLineTone = "neutral"


class InventoryContainerRowDTO(BaseModel):
    item_id: str
    icon: str | None = None
    name: str
    item_type: str
    filter_group: Literal["items", "resources", "quest"] = "items"
    weight: str = "-"
    quantity: int = 1
    rarity: str = "shared"
    rarity_tier: int = Field(default=0, ge=0, le=7)
    rarity_label: str = "Без грейда"
    equip_target: str | None = None
    valid_slots: list[str] = Field(default_factory=list)
    grid_w: int = 2
    grid_h: int = 1
    is_equipped: bool = False
    sync_state: str = "secured"
    is_unsecured: bool = False
    comparison: list[InventoryComparisonLineDTO] = Field(default_factory=list)
    details: InventoryItemDetailsDTO | None = None


class InventoryWindowDTO(BaseModel):
    char_id: int
    title: str = "Inventory"
    can_act: bool = True
    forbidden_reason: str | None = None
    avatar_url: str | None = None
    avatar_name: str = "NO_DATA"
    stats: InventoryStatsDTO = Field(default_factory=InventoryStatsDTO)
    body_zones: list[InventoryBodyZoneDTO]
    weapon_slots: list[InventoryWindowSlotDTO]
    accessory_rows: list[InventoryAccessoryRowDTO]
    quick_slots: list[InventoryQuickSlotDTO]
    tabs: list[InventoryTabDTO]
    visible_rows: list[InventoryContainerRowDTO]
    rows_visible_count: int = 10
    search_query: str | None = None
    search_placeholder: str = "Поиск"
    contract_state: str = "SHARED_INVENTORY_CONTRACT_V1"


class InventoryActionRequestDTO(BaseModel):
    char_id: int
    action: Literal["equip", "unequip", "move_to_belt", "remove_from_belt", "use", "drop"]
    item_id: str
    slot_id: str | None = None


class InventoryCloseRequestDTO(BaseModel):
    char_id: int


class InventoryActionForbiddenDTO(BaseModel):
    code: Literal["inventory_action_forbidden"] = "inventory_action_forbidden"
    message: str = "Вы не можете пользоваться инвентарём сейчас."
    state: str | None = None


EQUIPMENT_SLOTS: tuple[str, ...] = tuple(slot.value for slot in EquippedSlot)
BELT_SLOTS: tuple[str, ...] = tuple(slot.value for slot in QuickSlot)
