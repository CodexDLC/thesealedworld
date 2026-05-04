from typing import Any

from pydantic import BaseModel, Field

from src.shared.enums.inventory_enums import InventorySection
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
