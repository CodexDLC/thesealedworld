from enum import StrEnum
from typing import Any

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
    hp_percent: int | None = None  # Примерное HP
    image: str | None = None


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
