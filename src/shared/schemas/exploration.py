from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExplorationJsonDTO(BaseModel):
    model_config = ConfigDict(extra="allow")


# --- Request Models (API) ---


class MoveRequest(ExplorationJsonDTO):
    """Запрос на перемещение."""

    char_id: int
    direction: str | None = None
    target_id: str | None = None

    @model_validator(mode="after")
    def require_move_target(self) -> "MoveRequest":
        if not self.direction and not self.target_id:
            raise ValueError("Either direction or target_id is required")
        return self


class InteractRequest(ExplorationJsonDTO):
    """Запрос на взаимодействие."""

    char_id: int
    action: str
    target_id: str | None = None


class UseServiceRequest(ExplorationJsonDTO):
    """Запрос на использование сервиса."""

    char_id: int
    service_id: str


# --- Navigation Grid DTOs ---


class GridButtonDTO(ExplorationJsonDTO):
    """
    Кнопка навигационной сетки.
    """

    id: str  # Уникальный ID кнопки (например, "n", "search")
    label: str  # Текст на кнопке ("⬆️ Север", "🔍 Поиск")
    action: str  # API Action ("move:n", "interact:search")
    is_active: bool  # Доступна ли кнопка
    style: str = "primary"  # Стиль кнопки (primary, secondary, danger)
    tooltip: str | None = None


class NavigationGridDTO(BaseModel):
    """
    Раскладка клавиатуры навигации (3x3 + Services).
    """

    # Крестовина (Move)
    n: GridButtonDTO | None = None
    s: GridButtonDTO | None = None
    w: GridButtonDTO | None = None
    e: GridButtonDTO | None = None

    # Углы (Context)
    nw: GridButtonDTO | None = None
    ne: GridButtonDTO | None = None
    sw: GridButtonDTO | None = None
    se: GridButtonDTO | None = None

    # Центр
    center: GridButtonDTO | None = None

    # Нижний ряд (Services)
    services: list[GridButtonDTO] = Field(default_factory=list)


class NavigationActionsDTO(ExplorationJsonDTO):
    movement: dict[str, GridButtonDTO] = Field(default_factory=dict)
    exploration: dict[str, GridButtonDTO] = Field(default_factory=dict)
    services: dict[str, GridButtonDTO] = Field(default_factory=dict)
    auto_routes: dict[str, GridButtonDTO] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)


# --- Local Map DTOs ---


MapEdgeState = Literal["open", "blocked", "locked", "unknown"]


class ExplorationMapEdgeDTO(ExplorationJsonDTO):
    direction: Literal["north", "south", "west", "east"]
    state: MapEdgeState = "unknown"
    target_loc_id: str | None = None
    label: str | None = None
    travel_time: float | None = None
    tooltip: str | None = None


class ExplorationMapCellDTO(ExplorationJsonDTO):
    loc_id: str
    x: int
    y: int
    dx: int
    dy: int
    is_current: bool = False
    is_known: bool = False
    title: str | None = None
    description: str | None = None
    zone_id: str = ""
    terrain: str = ""
    node_type: str = ""
    is_safe_zone: bool = False
    system_connect: bool = False
    threat: float | None = None
    threat_tier: int | None = None
    dominant_anchor: str | None = None
    tags: list[str] = Field(default_factory=list)
    service_count: int = 0
    service_labels: list[str] = Field(default_factory=list)
    players_count: int = 0
    battles_count: int = 0
    corpse_count: int | None = None
    background_available: bool = False
    edges: dict[str, ExplorationMapEdgeDTO] = Field(default_factory=dict)
    render_edges: dict[str, ExplorationMapEdgeDTO] = Field(default_factory=dict)
    tooltip: dict[str, Any] = Field(default_factory=dict)


class ExplorationLocalMapDTO(ExplorationJsonDTO):
    char_id: int
    current_loc_id: str
    radius: int = 2
    size: int = 5
    rows: list[list[ExplorationMapCellDTO]] = Field(default_factory=list)


# --- HUD DTOs ---


class HudType(StrEnum):
    """Типы HUD."""

    EXPLORATION = "exploration"
    ALERT = "alert"


class BaseHudDTO(ExplorationJsonDTO):
    """Базовый HUD."""

    type: HudType


class ExplorationHudDTO(BaseHudDTO):
    """HUD исследования."""

    type: HudType = HudType.EXPLORATION
    threat: float = Field(default=0.0, ge=0.0, le=1.0)
    threat_tier: int = 0
    players_count: int = 0
    battles_count: int = 0
    is_safe_zone: bool = False
    system_connect: bool = False
    risk_state: str = "safe"
    pending_free_xp: float = 0.0
    pending_skill_count: int = 0
    carried_resource_count: int = 0
    carried_item_count: int = 0
    dominant_anchor: str | None = None
    ambient_tags: list[str] = Field(default_factory=list)


class AlertHudDTO(BaseHudDTO):
    """HUD уведомления."""

    type: HudType = HudType.ALERT
    message: str
    style: str = "warning"  # warning, info, error


# --- World DTO ---


class WorldNavigationDTO(ExplorationJsonDTO):
    """
    Полные данные для отрисовки экрана навигации (Карта).
    """

    # Core Info
    loc_id: str
    title: str
    description: str

    # Context
    visual_objects: list[str] = Field(default_factory=list)  # Объекты в тексте
    players_nearby: int = 0  # Legacy

    # UI Components
    grid: NavigationGridDTO
    navigation: NavigationActionsDTO | None = None  # Renamed from actions
    hud: ExplorationHudDTO | AlertHudDTO | None = None

    # UI Flags (Legacy)
    threat_tier: int = 0
    is_safe_zone: bool = False
    background_url: str | None = None
    anchor_influence: dict[str, Any] = Field(default_factory=dict)
    world_theme: Any | None = None
    zone_id: str = ""
    terrain: str = ""
    biome_id: str = ""
    node_type: str = ""
    zone_archetype: str = ""
    navigation_profile_id: str = ""
    buildable_kind: str | None = None
    landmark_profile: str | None = None
    movement_profile: dict[str, Any] = Field(default_factory=dict)
    world_zone: dict[str, Any] = Field(default_factory=dict)
    city_map: dict[str, Any] = Field(default_factory=dict)

    # Legacy Support
    metadata: dict[str, Any] = Field(default_factory=dict)


# --- List DTO ---


class ListItemDTO(ExplorationJsonDTO):
    """Элемент списка."""

    id: str
    text: str
    action: str  # Callback data при клике


class ExplorationListDTO(ExplorationJsonDTO):
    """
    DTO для отображения списков (Бои, Люди, Квесты).
    """

    title: str
    items: list[ListItemDTO]
    page: int
    total_pages: int
    back_action: str = "look_around"  # Куда ведет кнопка Назад


# --- Encounter DTOs ---


class EncounterType(StrEnum):
    """Типы энкаунтеров."""

    COMBAT = "COMBAT"
    NARRATIVE = "NARRATIVE"
    MERCHANT = "MERCHANT"
    QUEST = "QUEST"


class DetectionStatus(StrEnum):
    """Статус обнаружения."""

    AMBUSH = "AMBUSH"
    DETECTED = "DETECTED"


class EnemyPreviewDTO(ExplorationJsonDTO):
    """
    Превью врага в энкаунтере (зависит от Bestiary).
    """

    name: str | None = None  # "Волк" или "???"
    level: int | None = None
    member_tier: int | None = None
    threat_rating: int | None = None
    hp_percent: int | None = None  # Примерное HP
    image: str | None = None
    visual: dict[str, Any] = Field(default_factory=dict)


class EncounterOptionDTO(ExplorationJsonDTO):
    """
    Вариант действия в энкаунтере.
    """

    id: str  # ID действия ("attack", "flee")
    label: str  # Текст кнопки ("⚔️ Атаковать")
    style: str = "primary"  # Стиль кнопки


class EncounterDTO(ExplorationJsonDTO):
    """
    Данные события (Энкаунтера).
    """

    id: str
    type: EncounterType
    status: DetectionStatus | None = None  # DETECTED / AMBUSH

    title: str
    description: str
    image: str | None = None

    # Content
    enemies: list[EnemyPreviewDTO] = Field(default_factory=list)
    info_level: int = 0  # Уровень знаний (Bestiary)

    options: list[EncounterOptionDTO] = Field(default_factory=list)

    # Technical Data
    session_id: str | None = None  # ID боевой сессии (если бой)
    metadata: dict[str, Any] = Field(default_factory=dict)


# --- Screen Contract DTOs ---


class ExplorationScreenContextDTO(ExplorationJsonDTO):
    """Stable top-level exploration screen context."""

    loc_id: str
    title: str
    description: str
    background_url: str | None = None
    anchor_influence: dict[str, Any] = Field(default_factory=dict)
    world_theme: Any | None = None
    hud: ExplorationHudDTO | AlertHudDTO | None = None
    threat_tier: int = 0
    is_safe_zone: bool = False
    location_understanding_percent: float | None = None
    location_research_cap_reached: bool | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExplorationScreenContentDTO(ExplorationJsonDTO):
    """Lower exploration screen content supplied by navigation or encounter services."""

    kind: str
    data: Any


class ExplorationScreenDTO(ExplorationJsonDTO):
    """Composite payload for the exploration frontend."""

    context: ExplorationScreenContextDTO
    content: ExplorationScreenContentDTO
